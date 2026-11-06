#!/usr/bin/env python3
"""Bounded FX3 menu-repair guest observer. Frozen baseline is read-only."""
from pathlib import Path
import argparse
import re
import datetime
import fcntl
import hashlib
import json
import os
import plistlib
import resource
import shutil
import signal
import socket
import subprocess
import struct
import sys
import time
import uuid
from cpio_audit import audit
from osd_ring85_v3 import RingReader

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
FROZEN = Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm')
VOLUME_UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def input_check(item):
    p = Path(item['path'])
    if not p.is_file() or p.is_symlink() or digest(p) != item['sha256']:
        raise RuntimeError('Input SHA/path mismatch: ' + str(p))
    return p


def checkpoint(value):
    path = ROOT / 'STATE.json'
    state = json.loads(path.read_text()) if path.exists() else {}
    state.update(value)
    state['schema'] = 'fx3-menu-repair-runtime-checkpoint-v1'
    state['owner'] = '/root/fx3_vm_host'
    state['updated_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    temp = ROOT / 'STATE.json.tmp'
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidate', required=True, type=Path)
    ap.add_argument('--seconds', type=int, default=20)
    ap.add_argument('--trace-seconds', type=float, default=0)
    ap.add_argument('--label', default='guest')
    ap.add_argument('--icount-shift', type=int, choices=[0,1], default=None)
    ap.add_argument('--smp',type=int,choices=[1,4],default=1)
    ap.add_argument('--tcg-thread',choices=['single','multi'],default=None)
    ns = ap.parse_args()
    if ns.tcg_thread=='multi' and ns.icount_shift is not None:ap.error('QEMU11.1.2 rejects MTTCG with icount')
    if not 1 <= ns.seconds <= 600 or not 0 <= ns.trace_seconds <= 10:
        ap.error('Observation 1..600s, instruction trace 0..10s only')
    vol = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    if vol.get('VolumeUUID') != VOLUME_UUID:
        raise RuntimeError('External volume UUID mismatch')
    candidate_path = ns.candidate.resolve()
    if not candidate_path.is_relative_to(BASE):
        raise RuntimeError('Candidate manifest must be in this menu-repair task')
    candidate = json.loads(candidate_path.read_text())
    baseline = json.loads((FROZEN / 'manifest.json').read_text())
    checks = [(FROZEN / rel, h) for rel, h in baseline['runtime_sha256'].items()]
    checks.append((Path(baseline['kernel']['path']), baseline['kernel']['sha256']))
    for p, h in checks:
        input_check({'path': str(p), 'sha256': h})
    dtb = input_check(candidate['dtb'])
    initrd = input_check(candidate['initrd'])
    if not dtb.resolve().is_relative_to(BASE) or not initrd.resolve().is_relative_to(BASE):
        raise RuntimeError('Candidate DTB/initrd must be in this task')
    checks += [(dtb, candidate['dtb']['sha256']), (initrd, candidate['initrd']['sha256']),
               (candidate_path, digest(candidate_path))]
    snapshots = []
    fdt_bytes = dtb.read_bytes()
    fdt_header = struct.unpack_from('>10I', fdt_bytes)
    if fdt_header[0] != 0xd00dfeed or fdt_header[1] != len(fdt_bytes):
        raise RuntimeError('Malformed experimental FDT header')
    reserve_offset = fdt_header[4]
    while reserve_offset + 16 <= len(fdt_bytes):
        address, size = struct.unpack_from('>QQ', fdt_bytes, reserve_offset)
        reserve_offset += 16
        if not (address or size):
            break
        # Exact same-model Backup region was independently audited for07b.
        # This is read-only guest RAM, not a host source or physical device.
        if (address, size) == (0x404000000, 0x221000):
            snapshots.append({'address': address, 'size': size,
                              'name': 'backup-reserved-ram.bin',
                              'scope': 'Quiesced original Backup RAM only; not persistence/API acceptance'})
            snapshots.append({'address':address,'size':size,'name':'backup-after-shutdown.bin','scope':'AP88 final quiescedreservedBackup; shutdowncompletion separatelyverified; notAP89 input yet'})
        if (address, size) == (0x41d800000, 0x10000):
            snapshots.append({'address': address, 'size': size, 'name': 'capid-reserved-ram.bin', 'scope': 'Quiesced explicit virtual CAPID storage backing only; not CP/capture acceptance'})
        if (address, size) == (0x41d900000, 0x100000):
            snapshots.append({'address': address, 'size': size, 'name': 'dmm-virtual-ram.bin', 'scope': 'Quiesced explicit virtual two-slot DMM backing only; no originalCP/capture acceptance'})
        if (address, size) == (0x41dc00000, 0x10000):
            snapshots.append({'address': address, 'size': size, 'name': 'ui-gate-counters.bin', 'scope': 'Observer-only counters and boot records, double-bank published snapshot; no behavior model'})
        if (address, size) == (0x41dd00000, 0x90000):
            snapshots.append({'address':address,'size':size,'name':'face-dmm-reserved-ram.bin','scope':'Independent virtual face-registration byte storage; actual local-to-remote copy; no recognition/physical camera acceptance'})
        if (address,size)==(0x41e000000,0x1000000):
            snapshots.append({'address':address,'size':size,'name':'osd-ring-final.bin','scope':'Software OSD snapshot ring; no CP panel/compositor acceptance'})
        if (address, size) == (0x41da00000, 0x10000):
            snapshots.append({'address': address, 'size': size, 'name': 'adf-muted-ram.bin', 'scope': 'Explicit muted software backing; original_sound=0'})
    cpio_report = audit(initrd, FROZEN / 'share/fx3-original-app-loader-probe.cpio')
    audit_path = ROOT / ('preflight-' + digest(initrd)[:16] + '.json')
    if not audit_path.exists():
        audit_path.write_text(json.dumps(cpio_report, ensure_ascii=False, indent=2) + '\n')
    if not cpio_report['safe_to_unpack']:
        raise RuntimeError('CPIO unpack/order or original ELF identity gate failed: ' + str(audit_path))
    locks = []
    # Also take the baseline lock to coordinate any manual use of the shared runtime.
    for path, mode in [(FROZEN / '.run.lock', 'rb'), (ROOT / '.run.lock', 'a+b')]:
        lock = path.open(mode)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locks.append(lock)
    label = ''.join(c for c in ns.label if c.isalnum() or c in '-_')[:32]
    run = ROOT / 'runs' / (label + '-' + uuid.uuid4().hex[:8])
    run.mkdir()
    observer_dir = run / 'observer-source'
    observer_dir.mkdir()
    observer_sources = []
    for name in [Path(__file__).name, 'cpio_audit.py', 'decode_printk_ring.py', 'osd_ring85_v3.py']:
        shutil.copyfile(ROOT / name, observer_dir / name)
        observer_sources.append({'name': name, 'sha256': digest(observer_dir / name)})
    (run / 'cpio-audit.json').write_text(json.dumps(cpio_report, ensure_ascii=False, indent=2) + '\n')
    success_doc = BASE / 'success-cases/source/docs/tech/03-guest-environment.md'
    if success_doc.is_file():
        (run / 'success-path-provenance.json').write_text(json.dumps({
            'upstream_pinned_prefix': 'b3d7c1f', 'evidence_file': str(success_doc),
            'evidence_sha256': digest(success_doc),
            'evidence_section': 'section3 original devno→osal_utm→osal_uipc; original FX3 module/order/IDs checked separately',
            'application_to_FX3': 'Same module chain; no A7C2 binary offsets copied'}, ensure_ascii=False, indent=2) + '\n')
    qemu = FROZEN / baseline['binary']
    if 'qemu' in candidate:
        qemu = input_check(candidate['qemu'])
        if not qemu.resolve().is_relative_to(ROOT / 'qemu-display-build') or candidate.get('timer_model') is not True:
            raise RuntimeError('Unreviewed derived QEMU profile')
        checks.append((qemu, candidate['qemu']['sha256']))
    # Relative QMP sockaddr avoids the macOS AF_UNIX absolute-path length limit.
    args = [str(qemu), '-machine', 'virt,gic-version=2,secure=off', '-accel', 'tcg'+(',thread='+ns.tcg_thread if ns.tcg_thread else ''),
            '-cpu', 'cortex-a35', '-smp', str(ns.smp), '-m', str(candidate.get('memory_mib', 2048)), '-display', 'none',
            '-nodefaults', '-nic', 'none', '-no-reboot', '-monitor', 'none',
            '-serial', 'file:' + str(run / 'serial.log'),
            '-qmp', 'unix:q,server=on,wait=off', '-S',
            '-kernel', baseline['kernel']['path'], '-initrd', str(initrd),
            '-device', 'loader,file=' + str(dtb) + ',addr=0x400002000,force-raw=on']
    if 'initrd_load_address' in candidate:
        address = int(candidate['initrd_load_address'], 0)
        if address != 0x440000000 or candidate.get('memory_mib') != 5120:
            raise RuntimeError('Only reviewed high-initrd/5GiB experimental profile supported')
        index = args.index('-initrd')
        args[index:index+2] = ['-device', 'loader,file=' + str(initrd) + ',addr=0x440000000,force-raw=on']
    elif candidate.get('memory_mib', 2048) != 2048:
        raise RuntimeError('Unexpected memory profile')
    if ns.icount_shift is not None:
        args += ['-icount', f'shift={ns.icount_shift},align=off,sleep=off']
    if ns.trace_seconds:
        args += ['-d', 'in_asm', '-D', str(run / 'instruction.log')]
    env = os.environ.copy()
    env.update(baseline['model_env'])
    if candidate.get('timer_model') is True:
        env['FX3_VM_SONY_TIMER'] = '1'
    if candidate.get('scu_request_model') is True:
        env['FX3_VM_SCU_REQUEST'] = '1'
    if candidate.get('gpio_bank5_model') is True:
        env['FX3_VM_GPIO_BANK5'] = '1'
    command = {'args': args, 'cwd': str(run), 'model_env': {key: env[key] for key in ['FX3_VM_ESRAM_RAM', 'FX3_VM_HIGH_DDR', 'FX3_VM_SONY_TIMER', 'FX3_VM_SCU_REQUEST', 'FX3_VM_GPIO_BANK5'] if key in env},
               'candidate': str(candidate_path), 'candidate_sha256': digest(candidate_path),
               'seconds': ns.seconds, 'smp':ns.smp,'tcg_thread':ns.tcg_thread,'guest_original_thresholds_unchanged':True,'software_OSD_completion_explicit':True,'AP86B_native_CP_receiver_ownership_explicit':True, 'icount_profile': None if ns.icount_shift is None else f'shift={ns.icount_shift},align=off,sleep=off', 'trace_prefix_seconds': ns.trace_seconds,
               'read_only_guest_memory_snapshots': snapshots}
    (run / 'command.json').write_text(json.dumps(command, ensure_ascii=False, indent=2) + '\n')
    journal = []
    samples = []
    error = None
    early_stop_reason = None
    p = None
    seq = 0
    previous_cwd = Path.cwd()
    start = time.monotonic()
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def limits():
        resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024 * 1024, 32 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    def terminated(signum, frame):
        raise KeyboardInterrupt('Observer received signal ' + str(signum))

    signal.signal(signal.SIGTERM, terminated)

    with (run / 'host-stdout.log').open('wb') as stdout, (run / 'host-stderr.log').open('wb') as stderr:
        try:
            p = subprocess.Popen(args, cwd=run, env=env, stdout=stdout, stderr=stderr,
                                 start_new_session=True, preexec_fn=limits)
            checkpoint({'phase': 'RUNNING_BOUNDED_CANDIDATE', 'current_candidate': str(candidate_path),
                        'current_candidate_sha256': digest(candidate_path), 'current_run': str(run),
                        'fixed_inputs': [{'path': str(p), 'sha256': h} for p, h in checks],
                        'guest_process': {'pid': p.pid, 'current_running_pid': p.pid,
                                          'observer_pid': os.getpid(), 'exit': None, 'reaped': False},
                        'locks': [{'path': str(FROZEN / '.run.lock'), 'holder': os.getpid(), 'status': 'held'},
                                  {'path': str(ROOT / '.run.lock'), 'holder': os.getpid(), 'status': 'held'}],
                        'next_minimal_command': {'status': 'Current bounded observation in progress',
                                                 'argv': [sys.executable, str(Path(__file__)),
                                                          '--candidate', str(candidate_path), '--seconds',
                                                          str(ns.seconds), '--label', label]+(['--icount-shift',str(ns.icount_shift)] if ns.icount_shift is not None else [])}})
            for _ in range(100):
                if (run / 'q').exists() or p.poll() is not None:
                    break
                time.sleep(.05)
            if p.poll() is not None:
                raise RuntimeError('QEMU startup exited; inspect host-stderr.log')
            os.chdir(run)
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect('q')
            os.chdir(previous_cwd)
            f = s.makefile('rb')
            journal.append({'greeting': json.loads(f.readline())})

            def qmp(cmd, arguments=None):
                nonlocal seq
                seq += 1
                req = {'execute': cmd, 'id': seq}
                if arguments is not None:
                    req['arguments'] = arguments
                journal.append({'request': req, 'elapsed_seconds': time.monotonic() - start})
                s.sendall((json.dumps(req) + '\n').encode())
                while True:
                    raw = f.readline()
                    if not raw:
                        raise RuntimeError('QMP stream ended')
                    resp = json.loads(raw)
                    journal.append({'response': resp})
                    if resp.get('id') == seq:
                        return resp

            qmp('qmp_capabilities')
            qmp('human-monitor-command', {'command-line': 'info registers'})
            qmp('query-cpus-fast')
            qmp('cont')
            ring_reader=RingReader(run,qmp)
            last_ring_poll=0
            guest_start = time.monotonic()
            deadline = guest_start + ns.seconds
            tracing = ns.trace_seconds > 0
            first_draw_captured = False
            captured_draw_count = 0
            nonuniform_captured = False
            draw_captures = []
            uptime_samples=[]
            early_stop_reason = None
            replay_input_verified = False
            while time.monotonic() < deadline and p.poll() is None:
                if (run/'STOP_FOR_REVIEW').exists():
                    early_stop_reason=(run/'STOP_FOR_REVIEW').read_text()
                    break
                serial_now=(run/'serial.log').read_text(errors='replace')
                if 'FX3_AP89_BACKUP_REPLAY_VERIFIED' in serial_now and not replay_input_verified:
                    qmp('stop')
                    before_AP='FX3_AP_NATURAL_BOOTIN_BEGIN' not in serial_now
                    input_path=run/'ap89-input-before-AP.bin'
                    qmp('human-monitor-command',{'command-line':'pmemsave 0x404000000 0x221000 "'+str(input_path)+'"'})
                    got=digest(input_path);wanted=candidate['backup_replay']['sha256']
                    verified=got==wanted and before_AP
                    (run/'ap89-host-input-readback.json').write_text(json.dumps({'sha256':got,'expected':wanted,'before_AP_bootin_marker':before_AP,'verified':verified,'bytes':input_path.stat().st_size,'physical':'0x404000000','method':'QMPstop/pmemsave afterguesthelperremapSHA beforeAPlaunch;existingreservedRAMonly'},indent=2)+'\n')
                    if not verified:
                        early_stop_reason='AP89 independenthostRAMSHA or preAPtiming mismatch; stopbeforevalidation'
                        break
                    replay_input_verified=True
                    qmp('cont')
                seen_uptime=list(re.finditer(r'FX3_GUEST_UPTIME_SNAPSHOT\s*\n([0-9]+\.[0-9]+) ([0-9]+\.[0-9]+)',serial_now))
                for index,match in enumerate(seen_uptime):
                    if index>=len(uptime_samples):
                        uptime_samples.append({'sample':index+1,'guest_proc_uptime_seconds':float(match.group(1)),'guest_idle_seconds':float(match.group(2)),'host_elapsed_first_observed_seconds':time.monotonic()-guest_start,'scope':'Actual existing guest cat /proc/uptime; host first-observed timestamp includes polling and QMP pauses, not printk time'})
                        (run/'guest-uptime-samples.json').write_text(json.dumps(uptime_samples,indent=2)+'\n')
                if any(x in serial_now for x in ['FX3_OSD_PAIR_DEADLINE_EVIDENCE_END','FX3_OSD_ALLOC_DEADLINE_EVIDENCE_END','FX3_OSD_HEADLESS_REJECT','FX3_BACKUP_CP_OWNER_FAILED','FX3_AP89_REPLAY_FAILED','FX3_GPE_RESOURCE_BIND_REJECT','FX3_PRESET_CONTEXT_BIND_REJECT','FX3_GPE_EARLY_BIND_REJECT','FX3_BACKUP_CP_REJECT','FX3_BACKUP_CP_RETRY','FX3_SYS_UUD_REJECT','FX3_DISPLAY_BIND_FAIL','FX3_DISPLAY_SELFTEST_FAIL']):
                    early_stop_reason='AP86B explicit diagnostic/rejection gate; stop for review; no further protocol changes'
                    break
                if re.search(r'FX3_GPE_CMD [^\n]* result=[1-9][0-9]* ',serial_now):
                    early_stop_reason='AP90 first new GPE rejection; quiesce and review without further changes'
                    break
                if any(x in serial_now for x in ['Unhandled fault:','Entering exception monitor.','Kernel panic','symbol lookup error:']):
                    early_stop_reason='new guest fatal marker; quiesce snapshot quit immediately'
                    break
                st = subprocess.run(['ps', '-o', 'rss=,vsz=', '-p', str(p.pid)],
                                    capture_output=True, text=True)
                samples.append({'elapsed_seconds': time.monotonic() - start,
                                'rss_vsz_kib': st.stdout.strip()})
                if tracing and time.monotonic() - guest_start >= ns.trace_seconds:
                    qmp('human-monitor-command', {'command-line': 'log none'})
                    tracing = False

                if time.monotonic()-last_ring_poll>=1:
                    ring_reader.poll()
                    last_ring_poll=time.monotonic()
                time.sleep(.25)
            if p.poll() is None:
                qmp('stop')
                ring_reader.poll(final=True)
                if ('FX3_GPE_UNIFORM_DONE' in (run / 'serial.log').read_text(errors='replace') or any('FX3_GPE_CMD ' in line and 'result=0 ' in line for line in (run / 'serial.log').read_text(errors='replace').splitlines())):
                    snapshots.append({'address': 0x43feb5000, 'size': 0x140000, 'name': 'gpe-surface-545.bin', 'scope': 'Quiesced originalDMM545 surface after software uniform model; no UI acceptance'})
                for command in [
                    'gva2gpa 0xffffff80086e7538', 'gva2gpa 0xfffffffff13a1c38',
                    'x /2gx 0xffffff80086994d8', 'x /4gx 0xffffff80086e47a0',
                    'memsave 0xffffff80086994d8 0x10 "' + str(run / 'printk-pointers.bin') + '"',
                    'memsave 0xffffff80086e47a0 0x20 "' + str(run / 'printk-indices.bin') + '"',
                    'memsave 0xffffff80086e7538 0x20000 "' + str(run / 'printk-ring.bin') + '"',
                    'info registers']:
                    qmp('human-monitor-command', {'command-line': command})
                for snapshot in snapshots:
                    command = 'pmemsave ' + hex(snapshot['address']) + ' ' + hex(snapshot['size']) + ' "' + str(run / snapshot['name']) + '"'
                    qmp('human-monitor-command', {'command-line': command})
                kernel_text=(run/'serial.log').read_text(errors='replace')
                binding=re.search(r'FX3_OSAL_UIPC_BSS=(0x[0-9a-fA-F]+)',kernel_text)
                if binding:
                    kernel_bss=int(binding.group(1),16)
                    if 0xffffff8000000000<=kernel_bss<0xffffffc000000000:
                        for offset,count,name in [(0x3740,56,'osal-kernel-vpool.bin'),(0x98,9576,'osal-kernel-rtpool.bin')]:
                            target=run/name
                            qmp('human-monitor-command',{'command-line':f'memsave {hex(kernel_bss+offset)} {hex(count)} "{target}"'})
                        (run/'kernel-pool-binding.json').write_text(json.dumps({'source':'Read-only guest sysfs /sys/module/osal_uipc/sections/.bss','BSS':hex(kernel_bss),'audited_original_source':str(ROOT/'ap86-lifetime-original-proof.json'),'readback':'QMP memsave kernel virtual address, no host guest writes','vpool_offset':'0x3740','vpool_size':56,'rtpool_offset':'0x98','rtpool_size':9576},indent=2)+'\n')
                qmp('query-status')
                qmp('query-cpus-fast')
                qmp('quit')
            p.wait(timeout=5)
        except (Exception, KeyboardInterrupt) as exc:
            error = repr(exc)
        finally:
            os.chdir(previous_cwd)
            if p is not None and p.poll() is None:
                os.killpg(p.pid, signal.SIGTERM)
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait(timeout=3)
    (run / 'qmp.json').write_text(json.dumps(journal, ensure_ascii=False, indent=2) + '\n')
    ring_decode = None
    if all((run / n).is_file() for n in ['printk-pointers.bin', 'printk-indices.bin', 'printk-ring.bin']):
        dec = subprocess.run([sys.executable, str(ROOT / 'decode_printk_ring.py'), str(run)],
                             capture_output=True, text=True)
        ring_decode = {'exit': dec.returncode, 'stdout': dec.stdout, 'stderr': dec.stderr}
        (run / 'printk-decode-observer.json').write_text(json.dumps(ring_decode, indent=2) + '\n')
    serial = (run / 'serial.log').read_text(errors='replace') if (run / 'serial.log').exists() else ''
    exceptions = [m for m in ['Kernel panic', 'Entering exception monitor.', 'Unhandled fault:'] if m in serial]
    warnings = [line for line in serial.splitlines() if 'WARNING:' in line or 'BUG:' in line or 'Oops:' in line]
    markers = {m: m in serial for m in candidate.get('required_markers', [])}
    unchanged = all(digest(path) == h for path, h in checks)
    for snapshot in snapshots:
        path = run / snapshot['name']
        snapshot['present'] = path.is_file()
        if path.is_file():
            snapshot['actual_bytes'] = path.stat().st_size
            snapshot['sha256'] = digest(path)
    receipt = {'created_utc': started, 'duration_seconds': time.monotonic() - start,
               'candidate': str(candidate_path), 'candidate_sha256': digest(candidate_path),
               'observer_source_snapshot': observer_sources,
               'run': str(run), 'requested_seconds': ns.seconds,
               'qemu_pid': None if p is None else p.pid,
               'qemu_exit': None if p is None else p.returncode,
               'process_reaped': p is not None and p.poll() is not None,
               'inputs_unchanged': unchanged, 'input_checks': [{'path': str(p), 'sha256': h} for p, h in checks],
               'host_observer_error': error, 'memory_samples': samples,
               'printk_ring_decode': ring_decode,
               'read_only_guest_memory_snapshots': snapshots,
               'guest_exception_markers': exceptions, 'markers': markers,
               'guest_warning_lines': warnings,
               'menu_verified': False, 'classification': 'OBSERVATION_ONLY_REVIEW_GUEST_LOGS',
               'physical_devices_host_disks_network': 0,
               'early_stop_reason':early_stop_reason, 'receipt_scope': candidate.get('scope', 'Candidate original services/AP in bounded VM')}
    (run / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    for lock in locks:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    checkpoint({'phase': 'RUN_COMPLETE_REVIEW_PENDING', 'last_run': str(run), 'current_run': None,
                'last_run_immutable': True,
                'guest_process': {'pid': receipt['qemu_pid'], 'current_running_pid': None,
                                  'observer_pid': os.getpid(), 'exit': receipt['qemu_exit'],
                                  'reaped': receipt['process_reaped']},
                'inputs_unchanged': unchanged, 'guest_exception_markers': exceptions,
                'guest_warning_lines': warnings,
                'locks': [{'path': str(FROZEN / '.run.lock'), 'holder': None, 'status': 'released'},
                          {'path': str(ROOT / '.run.lock'), 'holder': None, 'status': 'released'}],
                'next_minimal_command': {'status': 'Review immutable serial/proc/ring before next candidate'}})
    print('RUN', run)
    print('OBSERVER', error, 'EXIT', receipt['qemu_exit'], 'REAPED', receipt['process_reaped'],
          'UNCHANGED', unchanged, 'GUEST_EXCEPTION', exceptions)
    print('\n'.join(serial.splitlines()[-100:]))
    return 0 if unchanged and error is None and receipt['process_reaped'] else 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print('Stopped:', exc, file=sys.stderr)
        sys.exit(2)
