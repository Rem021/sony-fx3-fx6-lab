#!/usr/bin/env python3
"""One bounded VM run of the new CP helper candidate on the fixed FX3 platform.

No browser, no deployment, no second Start. Uses the accepted early-kernel
QEMU/DTB/kernel/Backup and only replaces the CPIO CP helper member.
"""
import argparse
import datetime as dt
import fcntl
import json
import os
import plistlib
import resource
import signal
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
EARLY = HERE.parent
sys.path.insert(0, str(EARLY))
import fixed_runner as fr  # noqa: E402 - re-use the accepted QMP/lock/serial helpers

MANIFEST = HERE / 'vm-candidate-fbdiag.json'
MANIFEST_SHA_FILE = HERE / 'VM-CANDIDATE-FBDIAG-SHA256.txt'


def sha(path):
    return fr.sha(Path(path))


def check():
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    if volume.get('VolumeUUID') != fr.UUID:
        raise RuntimeError('wrong or unmounted external volume')
    manifest_sha = sha(MANIFEST)
    if manifest_sha != MANIFEST_SHA_FILE.read_text().strip():
        raise RuntimeError('vm candidate manifest changed')
    saved = json.loads(MANIFEST.read_text())
    if saved.get('status') != 'APPROVED_TWENTYFIRST_ONE_VM_PENDING_RUN':
        raise RuntimeError('candidate status is not approved')
    baseline_path = Path(saved['owner_baseline']['path'])
    if sha(baseline_path) != saved['owner_baseline']['sha256']:
        raise RuntimeError('owner baseline changed')
    baseline = json.loads(baseline_path.read_text())
    if saved['fx3_platform'] != baseline['platform_parameters']:
        raise RuntimeError('platform parameters changed')
    if saved['model_env'] != baseline['model_env']:
        raise RuntimeError('model environment changed')
    fixed = baseline['sha256']
    for key, item in (('dtb', fixed['fx3_dtb_full_binary']), ('backup', fixed['english_generation4_backup'])):
        if saved[key]['sha256'] != item['sha256'] or sha(item['path']) != item['sha256']:
            raise RuntimeError(key + ' changed')
    for key in ('kernel', 'initrd'):
        if sha(saved[key]['path']) != saved[key]['sha256']:
            raise RuntimeError(key + ' payload changed')
    changes = saved.get('firmware_payload_changes')
    if not isinstance(changes, list) or len(changes) != 2:
        raise RuntimeError('expected exactly kernel and CPIO payload changes')
    if changes[0]['role'] != 'kernel Image' or changes[1]['role'] != 'guest CPIO CP helper member':
        raise RuntimeError('unexpected payload roles')
    base_argv = baseline['fx3_vm_command'].copy()
    expected = base_argv.copy()
    expected[expected.index('-kernel') + 1] = saved['kernel']['path']
    for i, arg in enumerate(expected):
        if arg.startswith('loader,file=') and 'guest.cpio' in arg:
            expected[i] = 'loader,file=' + saved['initrd']['path'] + ',addr=0x440000000,force-raw=on'
    actual = saved['candidate_argv_before_observer_serial_retarget']
    if len(actual) != len(expected):
        raise RuntimeError('argv length changed')
    for a, b in zip(actual, expected):
        if a.startswith('file:') and 'serial.log' in a:
            continue
        if a != b:
            raise RuntimeError('argv differs beyond kernel/CPIO payload: ' + a)
    if actual[actual.index('-kernel') + 1] != saved['kernel']['path']:
        raise RuntimeError('kernel path mismatch')
    if not any('loader,file=' + saved['initrd']['path'] in a for a in actual):
        raise RuntimeError('CPIO loader path mismatch')
    return saved, manifest_sha


def run(saved, seconds):
    held = fr.acquire()
    process = None
    sock = None
    reader = None
    run_dir = HERE / 'runs' / ('cp-bind-' + uuid.uuid4().hex[:8])
    start = time.monotonic()
    reason = 'not_started'
    error = None
    startup_probe = {}
    cp_begin_at = None
    cp_rc_seen = None
    cp_rc0 = False
    cp_bind_marker = False
    ap_guard = False
    pre_ap_guard = False
    ap_markers = []
    try:
        run_dir.mkdir(parents=True, mode=0o700)
        args = saved['candidate_argv_before_observer_serial_retarget'].copy()
        args[args.index('-serial') + 1] = 'file:' + str(run_dir / 'serial.log')
        env = os.environ.copy()
        env.update(saved['model_env'])
        (run_dir / 'command.json').write_text(json.dumps({
            'argv': args, 'model_env': saved['model_env'],
            'manifest_sha256': sha(MANIFEST), 'mode': saved['mode'],
            'candidate': str(MANIFEST), 'runtime_owner_only': True,
            'approval': saved['approval'],
        }, ensure_ascii=False, indent=2) + '\n')
        with (run_dir / 'host-stdout.log').open('wb') as stdout, (run_dir / 'host-stderr.log').open('wb') as stderr:
            process = subprocess.Popen(args, cwd=run_dir, env=env, stdout=stdout, stderr=stderr,
                                       start_new_session=True, preexec_fn=fr.limits)
            deadline = time.monotonic() + seconds
            while not (run_dir / 'q').exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(.05)
            if process.poll() is not None:
                raise RuntimeError('QEMU exited before QMP setup')
            if time.monotonic() >= deadline:
                raise TimeoutError('QMP setup timeout')
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(3)
            fr.connect_relative(sock, run_dir)
            reader = sock.makefile('rb')
            json.loads(reader.readline())
            fr.qmp_send(sock, reader, 'qmp_capabilities', 1)
            regs = fr.qmp_send(sock, reader, 'human-monitor-command', 2,
                               {'command-line': 'info registers'}).get('return', '')
            startup_probe['registers'] = regs
            if 'PC=0000000400000000' not in regs or 'X00=0000000000000000' not in regs:
                raise RuntimeError('pre-cont PC/x0 differs from pinned historical QMP startup')
            cpus = fr.qmp_send(sock, reader, 'query-cpus-fast', 3).get('return', [])
            startup_probe['cpu_count'] = len(cpus)
            if len(cpus) != saved['fx3_platform']['smp'] or any(
                    x.get('qom-type') != 'cortex-a35-arm-cpu' for x in cpus):
                raise RuntimeError('pre-cont CPU topology differs from baseline')
            fr.qmp_send(sock, reader, 'cont', 4)
            reason = 'wall_timeout'
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    reason = 'qemu_exited'
                    break
                serial = (run_dir / 'serial.log').read_bytes() if (run_dir / 'serial.log').exists() else b''
                obs = fr.serial_observation(serial)
                text = serial.decode('utf-8', 'replace')
                if obs['fault_markers']:
                    reason = 'kernel_fault_marker'
                    break
                if obs['cpuset_not_ready']:
                    reason = 'cpuset_not_ready'
                    break
                if obs['ap_guard']:
                    ap_guard = True
                    reason = 'ap_guard_observed_continue'
                    # ap-window: do not stop at AP guard; keep collecting AP serial.
                for marker in ('FX3_AP_IM_ENDMAPS','FX3_AP89_UUD_DECISION','FX3_AP89_SCREEN_CREATE','FX3_MEDIA_START_BRANCH','FX3_RM_NATIVE_FREE'):
                    if marker in text and marker not in ap_markers:
                        ap_markers.append(marker)
                if 'FX3_BACKUP_CP_INSMOD_RC=0' in text:
                    cp_rc0 = True
                if obs['pre_cp_first_negative_line']:
                    reason = 'pre_cp_first_negative'
                    break
                if 'FX6_SYNC100_AGNOSTIC_BIND' in text:
                    cp_bind_marker = True
                if 'FX3_UTIMER_BEGIN' in text:
                    pre_ap_guard = True
                if b'FX3_BACKUP_CP_INSMOD_RC=0' in serial:
                    cp_rc0 = True
                    if cp_rc_seen is None:
                        cp_rc_seen = 0
                if obs['cp_helper_rc_line'] is not None:
                    cp_rc_seen = obs['cp_helper_rc']
                    if cp_rc_seen != 0:
                        reason = 'cp_helper_insmod_rc'
                        break
                    cp_rc0 = True
                if obs['cp_helper_begin'] and cp_begin_at is None:
                    cp_begin_at = time.monotonic()
                if cp_begin_at is not None and cp_rc_seen is None and not cp_rc0 and time.monotonic() - cp_begin_at >= 40:
                    reason = 'cp_helper_no_rc_40s'
                    break
                time.sleep(.025)
    except BaseException as exc:
        error = repr(exc)
        if isinstance(exc, KeyboardInterrupt):
            reason = 'interrupted'
        elif isinstance(exc, TimeoutError):
            reason = 'wall_timeout'
        else:
            reason = 'error'
    finally:
        if sock is not None and reader is not None:
            try:
                fr.qmp_send(sock, reader, 'quit', 5)
            except Exception:
                pass
        if process is not None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=3)
        if reader is not None:
            reader.close()
        if sock is not None:
            sock.close()
        for stream in reversed(held):
            fcntl.flock(stream, fcntl.LOCK_UN)
            stream.close()
    logs = {name: {'bytes': (run_dir / name).stat().st_size, 'sha256': sha(run_dir / name)}
            for name in ('serial.log', 'host-stdout.log', 'host-stderr.log') if (run_dir / name).exists()}
    final_serial = (run_dir / 'serial.log').read_bytes() if (run_dir / 'serial.log').exists() else b''
    observed = fr.serial_observation(final_serial)
    result = {
        'schema': 'fx6-hybrid-fx3kernel-fbdiag-run-v1',
        'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'manifest_sha256': sha(MANIFEST),
        'mode': saved['mode'],
        'reason': reason,
        'serial_observation': observed,
        'cp_bind_marker': cp_bind_marker,
        'cp_helper_rc': cp_rc_seen,
        'cp_helper_rc0': cp_rc0,
        'pre_ap_guard': pre_ap_guard,
        'ap_guard': ap_guard,
        'ap_markers': ap_markers,
        'startup_probe': startup_probe,
        'elapsed_seconds': time.monotonic() - start,
        'maximum_seconds': seconds,
        'qemu_pid': None if process is None else process.pid,
        'qemu_exit': None if process is None else process.returncode,
        'process_reaped': process is None or process.poll() is not None,
        'locks_released': True,
        'logs': logs,
        'error': error,
        'firmware_AP_CP_AV_result': ('AP_MARKER_OBSERVED_MENU_NOT_PROVEN' if ap_markers else ('CP_RC0_OBSERVED_NOT_AP' if cp_rc0 else 'NOT_TESTED')),
        'polling_is_not_CPU_breakpoint': True,
        'one_VM_one_Start': True,
        'deployment': False,
    }
    (run_dir / 'run-receipt.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    return result


def main():
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true', help='hash and argv audit only; no locks or QEMU')
    group.add_argument('--run', action='store_true', help='one approved VM run only')
    ap.add_argument('--seconds', type=int, default=180)
    ns = ap.parse_args()
    if not 1 <= ns.seconds <= 180:
        ap.error('seconds must be 1..180')
    saved, manifest_sha = check()
    if ns.check:
        print(json.dumps({
            'status': 'PASS_OFFLINE_ONE_VM_CANDIDATE',
            'manifest_sha256': manifest_sha,
            'kernel_sha256': saved['kernel']['sha256'],
            'initrd_sha256': saved['initrd']['sha256'],
            'payload_changes': saved['firmware_payload_changes'],
            'runtime_started': False,
        }, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(run(saved, ns.seconds), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
