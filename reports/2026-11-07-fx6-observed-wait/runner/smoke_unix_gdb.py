#!/usr/bin/env python3
"""Owned stopped QEMU without Sony guest/locks/TCP; check the Unix RSP endpoint."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import socket
import subprocess
import tempfile
import time


def fingerprint(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4*1024*1024), b''):
            h.update(b)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


def request(sock, payload):
    b = payload.encode('ascii')
    sock.sendall(b'$'+b+b'#'+f'{sum(b)%256:02x}'.encode())
    def exact(n):
        out = b''
        while len(out) < n:
            chunk = sock.recv(n-len(out))
            if not chunk:
                raise RuntimeError('RSP closed')
            out += chunk
        return out
    while exact(1) != b'$':
        pass
    data = bytearray()
    while True:
        c = exact(1)
        if c == b'#':
            break
        data += c
    checksum = int(exact(2), 16)
    if checksum != sum(data)%256:
        raise RuntimeError('RSP response checksum mismatch')
    sock.sendall(b'+')
    return data.decode('ascii')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--qemu', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    volume = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    if volume.get('VolumeUUID') != 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':
        raise RuntimeError('external volume mismatch')
    root = Path(__file__).resolve().parent
    if args.output.resolve().parent != root:
        raise RuntimeError('evidence output must stay in v2 directory')
    spec = importlib.util.spec_from_file_location('runner_v2', root/'run_observer_once.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    manifest = json.loads(args.manifest.read_text())
    protected = [args.manifest, Path(manifest['initrd']['path']), args.manifest.parent/'appfw-launch-observer',
                 args.manifest.parent/'candidate-init.sh']
    before = [fingerprint(p) for p in protected]
    result = {'schema':'fx6-runner-v2-unix-smoke-v1', 'qemu':fingerprint(args.qemu),
        'scope':'No Sony kernel/DTB/CPIO/backup loaded; CPU stays stopped; no shared locks; Unix sockets only',
        'frozen_inputs_before':before, 'requests':[]}
    proc = None
    try:
        with tempfile.TemporaryDirectory(prefix='smoke-', dir=root) as name:
            run = Path(name).resolve()
            argv = [str(args.qemu.resolve()), '-machine','virt,gic-version=2,secure=off',
                '-accel','tcg,thread=single','-cpu','cortex-a35','-smp','1','-m','64',
                '-display','none','-nodefaults','-nic','none','-monitor','none','-serial','none','-S',
                '-chardev','socket,path=g,server=on,wait=off,id=keygate93','-gdb','chardev:keygate93']
            assert '-s' not in argv and '-kernel' not in argv and '-device' not in argv
            assert argv[argv.index('-gdb')+1] == 'chardev:keygate93'
            result['argv'] = argv
            with (run/'stdout').open('wb') as out, (run/'stderr').open('wb') as err:
                proc = subprocess.Popen(argv, cwd=run, stdout=out, stderr=err)
                end = time.monotonic()+5
                while not (run/'g').exists() and proc.poll() is None and time.monotonic() < end:
                    time.sleep(.02)
                if not (run/'g').exists():
                    raise RuntimeError('Unix g socket absent: '+(run/'stderr').read_text(errors='replace'))
                result['unix_socket_created'] = True
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(3)
                old = Path.cwd()
                try:
                    os.chdir(run)
                    sock.connect('g')  # Same relative endpoint expected by InputGate.
                finally:
                    os.chdir(old)
                try:
                    for q in ['qSupported','?']:
                        reply = request(sock, q)
                        result['requests'].append({'request':q,'reply':reply})
                        if q == 'qSupported' and 'PacketSize=' not in reply:
                            raise RuntimeError('missing qSupported capabilities')
                        if q == '?' and not reply.startswith(('T','S')):
                            raise RuntimeError('missing stopped reply')
                finally:
                    sock.close()
                proc.terminate()
                proc.wait(timeout=5)
            result['qemu_exit'] = proc.returncode
            result['host_stderr'] = (run/'stderr').read_text(errors='replace')
            result['host_stdout'] = (run/'stdout').read_text(errors='replace')
            # check() verifies input bytes but never calls execute()/acquire()/Popen().
            new = dict(manifest)
            new['created_utc'] = 'offline-test-new-manifest-sha-only'
            new['candidate_argv_before_observer_serial_retarget'] = runner.normalize_gdb_argv(
                manifest['candidate_argv_before_observer_serial_retarget'])
            new_path = run/'new-manifest-check-only.json'
            new_path.write_text(json.dumps(new,indent=2)+'\n')
            new_sha = fingerprint(new_path)['sha256']
            runner.check(new_path, new_sha)
            result['new_manifest_check'] = {'passed':True,'sha256':new_sha,
                'differs_from_old':new_sha!=fingerprint(args.manifest)['sha256'],
                'no_guest_execution':True,'already_normalized_argv_accepted':True}
        result['temporary_smoke_directory_removed'] = not run.exists()
        result['frozen_inputs_unchanged'] = before == [fingerprint(p) for p in protected]
        assert result['frozen_inputs_unchanged']
        result['passed'] = True
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait(timeout=3)
        result['owned_process_reaped'] = proc is None or proc.poll() is not None
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':True,'owned_process_reaped':result['owned_process_reaped'],
        'evidence':str(args.output)},ensure_ascii=False))


if __name__ == '__main__':
    main()
