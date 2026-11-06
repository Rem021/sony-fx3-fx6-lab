#!/usr/bin/env python3
"""AP103 software LDEC and native save diagnostic; AP102 observer transport retained."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "menu-repair-01/runtime"))
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
from osd_ring93_v4 import RingReader
from key_readback103_v1 import capture_frame
from gate_input105_v1 import InputGate,valid_command,KernelObserver
from file_readback100 import capture as capture_native_file
from restore_api103_v2 import restore_native_api

ROOT = Path(__file__).resolve().parents[3] / "menu-repair-01/runtime"
OUT = Path(__file__).resolve().parent
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
    path = OUT / 'vmopt-20261103-STATE.json'
    state = json.loads(path.read_text()) if path.exists() else {}
    state.update(value)
    state['schema'] = 'fx3-menu-repair-runtime-checkpoint-v1'
    state['owner'] = '/root/fx3_vm_host'
    state['updated_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    temp = OUT / 'vmopt-20261103-STATE.json.tmp'
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
    if not 1 <= ns.seconds <= 1800 or not 0 <= ns.trace_seconds <= 10:
        ap.error('Observation 1..1800s, instruction trace 0..10s only')
    vol = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    if vol.get('VolumeUUID') != VOLUME_UUID:
        raise RuntimeError('External volume UUID mismatch')
    candidate_path = ns.candidate.resolve()
    if not candidate_path.is_relative_to(BASE):
        raise RuntimeError('Candidate manifest must be in this menu-repair task')
    candidate = json.loads(candidate_path.read_text())
    native_seed=input_check(candidate['native_Backup_seed'])
    input_check(candidate['ap102_contract']['original_proof'])
    if candidate['ap103_contract']['authority']!='msg_29cd3974555b': raise RuntimeError('Missing AP103 authority')
    input_check(candidate['ap103_contract']['decoder_core'])
    if candidate.get('ap105_contract',{}).get('authority')!='msg_719755e33697':raise RuntimeError('Missing AP105 authority')
    input_check(candidate['ap105_contract']['performance_so'])
    baseline = json.loads((FROZEN / 'manifest.json').read_text())
    checks = [(FROZEN / rel, h) for rel, h in baseline['runtime_sha256'].items()]
    checks.append((Path(baseline['kernel']['path']), baseline['kernel']['sha256']))
    checks.append((native_seed,candidate['native_Backup_seed']['sha256']))
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
        if (address, size) == (0x41df00000, 0x10000):
            snapshots.append({'address':0x41df01000,'size':0x6000,'name':'date98-trace-final.bin','scope':'Read-only observer-output copy only, native user32 and kernel44; first4K input unchanged'})
            snapshots.append({'address':0x41df08000,'size':0x1000,'name':'date99-clock-final.bin','scope':'Software CP clock plus native ready/type2 request/reply/type4 trace; no originalCP address'})
            snapshots.append({'address':address,'size':256,'name':'ap102-control-final.bin','scope':'Read-only final hoststep command/done header'})
        if (address, size) == (0x41da00000, 0x10000):
            snapshots.append({'address': address, 'size': size, 'name': 'adf-muted-ram.bin', 'scope': 'Explicit muted software backing; original_sound=0'})
    cpio_report = audit(initrd, FROZEN / 'share/fx3-original-app-loader-probe.cpio')
    audit_path = OUT / ('preflight-' + digest(initrd)[:16] + '.json')
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
    run = OUT / 'runs' / (label + '-' + uuid.uuid4().hex[:8])
    run.mkdir()
    run.chmod(0o700)
    observer_dir = run / 'observer-source'
    observer_dir.mkdir()
    observer_sources = []
    for name in [Path(__file__).name, 'cpio_audit.py', 'decode_printk_ring.py', 'osd_ring93_v4.py','key_readback103_v1.py','gate_input101.py','file_readback100.py','trial_ring_v1.py','restore_api103_v2.py','gate_input105_v1.py']:
        shutil.copyfile((Path(__file__) if name == Path(__file__).name else ROOT / name), observer_dir / name)
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
            '-qmp', 'unix:q,server=on,wait=off', '-chardev','socket,path=g,server=on,wait=off,id=keygate93','-gdb','chardev:keygate93','-S',
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
               'extended_runtime_authority':'msg_4e88c7b0d2b2','retained_guest_key_limit':30, 'seconds': ns.seconds, 'smp':ns.smp,'tcg_thread':ns.tcg_thread,'guest_original_thresholds_unchanged':True,'software_OSD_completion_explicit':True,'AP86B_native_CP_receiver_ownership_explicit':True, 'icount_profile': None if ns.icount_shift is None else f'shift={ns.icount_shift},align=off,sleep=off', 'trace_prefix_seconds': ns.trace_seconds,
               'read_only_guest_memory_snapshots': snapshots}
    (run / 'command.json').write_text(json.dumps(command, ensure_ascii=False, indent=2) + '\n')
    journal = []
    samples = []
    error = None
    early_stop_reason = None
    p = None
    kernel_observer = None
    input_gate = None
    qmp = None
    seq = 0
    previous_cwd = Path.cwd()
    start = time.monotonic()
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def limits():
        resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024 * 1024, 256 * 1024 * 1024))
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
            input_gate=InputGate(run,delete_key=int(candidate.get("host_step_contract",{}).get("delete_key","0"),0))
            kernel_observer=KernelObserver(run,input_gate,qmp,json.loads((ROOT/"ap102-observer-original-proof-v1.json").read_text()))
            phaseA_capture=None
            last_screen_count=0
            last_screen_observed_at=guest_start
            host_step=0
            up_seen={}
            step_captures=[]
            phaseA_proof={}
            next_native_file=guest_start+20
            native_file_reads=[]

            while time.monotonic() < deadline and p.poll() is None:
                handled104=kernel_observer.poll()
                if kernel_observer.first_unfetched is not None:
                    early_stop_reason='AP104 first native unfetched captured at original error instruction; no further input';break
                if handled104:continue
                if (run/'STOP_FOR_REVIEW').exists():
                    early_stop_reason=(run/'STOP_FOR_REVIEW').read_text()
                    break
                serial_now=(run/'serial.log').read_text(errors='replace')
                if 'unfetched'in serial_now or re.search(r'FX3_LIGHT104_ALLOC_RETURN[^\n]*result=-1018(?: |$)',serial_now):
                    early_stop_reason='AP105 first observed native unfetched/alloc -1018; stop promptly; later guest calls may precede host UART observation';break
                uipc104=re.search(r'FX3_UIPC104_TEXT_BASE=(0x[0-9a-fA-F]+)',serial_now)
                if uipc104 and 'uipc'not in kernel_observer.module_bases:
                    qmp('stop');kernel_observer.install_uipc(int(uipc104[1],16));qmp('cont')
                gpe104=re.search(r'FX3_GPE104_LIB_BIND base=(0x[0-9a-fA-F]+)',serial_now)
                if gpe104 and 'gpe'not in kernel_observer.module_bases:
                    qmp('stop');kernel_observer.install_gpe(int(gpe104[1],16));qmp('cont')
                binding102=re.search(r'FX3_BACKUP102_TEXT_BASE=(0x[0-9a-fA-F]+)',serial_now)
                if binding102 and kernel_observer.base is None:
                    qmp('stop');kernel_observer.install(int(binding102[1],16));qmp('cont')
                if re.search(r'FX3_SYNC100_REJECT|FX3_SYNC100_DISABLED|FX3_TOUCH100_REJECT|FX3_PRESET_CONTEXT_BIND_REJECT|FX3_SYNC100_API_BIND[^\n]*result=-',serial_now):
                    early_stop_reason='AP100 new device contract or observer binding rejected; no further input';break
                if time.monotonic()>=next_native_file:
                    qmp('stop');native_file_reads.append(capture_native_file(qmp,run,'periodic-%02d'%len(native_file_reads)));qmp('cont');next_native_file=time.monotonic()+20
                if 'FX3_DATE99_REJECT' in serial_now:
                    early_stop_reason='AP99 CP date model rejected/failed transaction; no further input';break
                if any(t in serial_now for t in ['FX3_LDEC103_INIT_FAILED','FX3_LDEC103_SELFTEST_FAILED']):
                    early_stop_reason='AP103 software device or real ioctl selftest failed';break
                ldec_live=serial_now.split('FX3_LDEC103_GUEST_IOCTL_SELFTEST_PASS',1)
                if len(ldec_live)==2 and re.search(r'FX3_LDEC103_IOCTL[^\n]*result=-[0-9]+',ldec_live[1]):
                    early_stop_reason='AP103 actual resource ioctl rejected; capture blocker before further input';break
                if re.search(r'assert at|Assertion|exception monitor|FX3_SIGNAL_OBSERVE[^\n]*signal=6(?: |$)',serial_now,re.I):
                    early_stop_reason='AP97 native assertion/abort/exception marker; stop before any further key';break
                if re.search(r'FX3_RM_[A-Z_]*REJECT|FX3_RM_UNKNOWN|unknown\s+key|invalid\s+from_type',serial_now,re.I):
                    early_stop_reason='AP93 explicit RM/input rejection or new unsupported request; preserve evidence and escalate'
                    break
                if 'FX3_MEDIA_INIT_TIMEOUT' in serial_now or re.search(r'FX3_MEDIA_NOTIFY [^\n]*status=1 ',serial_now):
                    early_stop_reason='AP93 empty-slot native initialization acceptance failed; no keys'
                    break
                if 'FX3_MEDIA_MOUNT_ENTER' in serial_now or 'MOUNT_ERR_EXTMEDIA_SLOT' in serial_now:
                    early_stop_reason='AP93 unexpected native mount/error in empty boot; no keys'
                    break
                opens=list(re.finditer(r'FX3_AP89_SCREEN_OPEN_ENTER [^\n]*id2=(0x[0-9a-f]+)',serial_now))
                if len(opens)!=last_screen_count:
                    last_screen_count=len(opens);last_screen_observed_at=time.monotonic()
                for match in re.finditer(r'FX3_SYNTH_KEY step=(\d+) key=(0x[0-9a-f]+) status=0 [^\n]*result=0 ',serial_now):
                    step=int(match[1]);key=int(match[2],0)
                    if step not in up_seen:up_seen[step]=(time.monotonic(),key)
                for step,(at,key) in sorted(up_seen.items()):
                    if not any(x['step']==step for x in step_captures) and time.monotonic()-at>=2:
                        qmp('stop');ring_reader.poll()
                        captured=capture_frame(qmp,run,f'step-{step:02d}-key-{key:03x}',step,key,at)
                        trace_path=run / ('date98-trace-step-%02d.bin' % step)
                        qmp('human-monitor-command',{'command-line':'pmemsave 0x41df01000 0x6000 '+chr(34)+str(trace_path)+chr(34)})
                        qmp('human-monitor-command',{'command-line':'pmemsave 0x41df08000 0x1000 '+chr(34)+str(run / ('date99-clock-step-%02d.bin' % step))+chr(34)})
                        step_captures.append(captured);(run/'ap102-step-readbacks.json').write_text(json.dumps(step_captures,indent=2)+'\n');qmp('cont')
                        if captured.get('error'):
                            early_stop_reason='AP95 per-step QMP readback failed';break
                if early_stop_reason:break
                if phaseA_capture is None and opens and time.monotonic()-last_screen_observed_at>=10 and (run/'osd-ring-readback.json').exists():
                    branches=re.findall(r'FX3_MEDIA_START_BRANCH [^\n]*state=(\d+)',serial_now)
                    notify=re.findall(r'FX3_MEDIA_NOTIFY [^\n]*mediaID=(0x[0-9a-f]+) [^\n]*status=(\d+)',serial_now)
                    freed=re.findall(r'FX3_RM_NATIVE_FREE [^\n]*bytes=(\d+) [^\n]*result=0 ',serial_now)
                    valid=branches==['2','2'] and sorted(notify)==[('0x1000','0'),('0x1010','0')] and all(str(n) in freed for n in [136,28,7]) and 'FX3_KEY96_READY' in serial_now and 'FRONT_FULL_BODY' in serial_now and 'raw=02000007000000 ' in serial_now and opens[-1][1] not in ['0x2ae','0x2af','0x2c7']
                    if valid:
                        qmp('stop');ring_reader.poll();phaseA_capture=capture_frame(qmp,run,'phaseA-before-SETUP',0,0,last_screen_observed_at)
                        phaseA_proof={'branches':branches,'native_notifications':notify,'native_free_sizes':freed,'last_native_screen':opens[-1][1],'host_seconds_since_last_observed_open':time.monotonic()-last_screen_observed_at,'no_Mount':True,'no_MOUNT_ERR':True,'no_INIT_TIMEOUT':True,'no_keys_in_phaseA':not up_seen,'QMP':phaseA_capture};(run/'ap102-phaseA.json').write_text(json.dumps(phaseA_proof,indent=2)+'\n')
                        if phaseA_capture.get('error'):
                            early_stop_reason='AP93 phaseA QMP readback failed';break
                        qmp('cont')
                backup_request=run/'ap102-save-backup.json'
                if backup_request.exists() and not (run/'ap102-backup-after-setup-v2.json').exists():
                    request=json.loads(backup_request.read_text())
                    if request.get('authorization')!='msg_7eb2cdbf663a' or request.get('step')!=host_step or not step_captures or step_captures[-1]['step']!=host_step or not isinstance(request.get('observed_page'),str) or not request['observed_page'].strip():
                        early_stop_reason='AP95 invalid preMENU Backup snapshot request';break
                    qmp('stop')
                    path=run/'backup-after-setup-v2.bin'
                    assert not path.exists()
                    answer=qmp('human-monitor-command',{'command-line':f'pmemsave 0x404000000 0x221000 "{path}"'})
                    if not path.exists() or path.stat().st_size!=0x221000:
                        early_stop_reason='AP95 preMENU Backup snapshot failed';break
                    force_bytes=path.read_bytes()
                    force_zero=force_bytes[0x8eb51]==0 and force_bytes[0x6e7ac]==0
                    if not force_zero:
                        early_stop_reason='AP99 standby rawRAM force keys not both0; preserve snapshot, no MENU';break
                    proof={'path':str(path),'physical':'0x404000000','bytes':path.stat().st_size,'sha256':digest(path),'host_step':host_step,'observed_page':request['observed_page'],'observed_png':request.get('observed_png'),'MENU_not_yet_sent':not any(x['key']=='0x1ab' for x in input_gate.history),'QMP_read_only':True,'original_seed_unchanged':True,'raw_live_RAM_not_validated_storage_file':True,'force_zero_verified':force_zero,'force_AP_02cf0014':force_bytes[0x8eb51],'force_mirror_01070140':force_bytes[0x6e7ac],'authority':'msg_7eb2cdbf663a'}
                    native_file_reads.append(capture_native_file(qmp,run,'before-menu'))
                    (run/'ap102-backup-after-setup-v2.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
                    qmp('cont')
                state_request=run/'ap102-observe-state.json'
                if state_request.exists():
                    request=json.loads(state_request.read_text());label102=request.get('label','')
                    if not re.fullmatch(r'[a-z0-9-]{1,40}',label102) or (request.get('step')!=host_step and not (run/('ap102-'+label102+'-state.json')).exists()):
                        raise RuntimeError('Invalid AP102 read-only state request')
                    target102=run/('ap102-'+label102+'-state.json')
                    if not target102.exists():
                        qmp('stop');ram102=run/('ap102-'+label102+'-Backup-RAM.bin');qmp('human-monitor-command',{'command-line':'pmemsave 0x404000000 0x221000 "'+str(ram102)+'"'});file102=capture_native_file(qmp,run,label102);qmp('cont');raw102=ram102.read_bytes();target102.write_text(json.dumps({'host_monotonic':time.monotonic(),'step':host_step,'label':label102,'RAM':str(ram102),'RAM_SHA256':digest(ram102),'language_RAM':raw102[0x8dd85],'force_keys':[raw102[0x8eb51],raw102[0x6e7ac]],'native_file':file102,'observation_only':True},indent=2)+'\n')
                view_request=run/'ap102-capture-current.json'
                if view_request.exists():
                    request=json.loads(view_request.read_text());label=request.get('label','')
                    if not re.fullmatch(r'[a-z0-9-]{1,40}',label) or (request.get('step')!=host_step and not (run/('ap102-'+label+'.json')).exists()):
                        early_stop_reason='AP95 invalid extra read-only frame request';break
                    if not (run/('ap102-'+label+'.json')).exists():
                        qmp('stop');ring_reader.poll();extra=capture_frame(qmp,run,label,host_step,0,time.monotonic());qmp('human-monitor-command',{'command-line':'pmemsave 0x41df08000 0x1000 '+chr(34)+str(run / ('date99-clock-'+label+'.bin'))+chr(34)});qmp('human-monitor-command',{'command-line':'pmemsave 0x41df01000 0x6000 '+chr(34)+str(run / ('date98-trace-'+label+'.bin'))+chr(34)});qmp('cont')
                        if extra.get('error'):
                            early_stop_reason='AP95 additional current-frame readback failed';break
                if phaseA_capture is not None and 'gpe'in kernel_observer.module_bases and host_step<30 and (host_step==0 or step_captures and step_captures[-1]['step']==host_step and time.monotonic()-up_seen[host_step][0]>=4):
                    proposed_path=run/'ap102-next-key.json'
                    if proposed_path.exists():
                        try:proposed=json.loads(proposed_path.read_text())
                        except (ValueError,TypeError):
                            early_stop_reason='AP95 malformed single-step JSON';break
                        if proposed.get('step')==host_step+1:
                            try:key=int(proposed['key'],0)
                            except (KeyError,ValueError,TypeError):
                                early_stop_reason='AP95 invalid single-step key before any guest write';break
                            hold_ms=proposed.get('hold_ms');description=proposed.get('observed_page');reason_text=proposed.get('reason')
                            if proposed.get('authorization')!='msg_7eb2cdbf663a' or not isinstance(hold_ms,int) or not valid_command(host_step+1,key,hold_ms,host_step,input_gate.delete_key) or not isinstance(description,str) or not description.strip() or not isinstance(reason_text,str) or not reason_text.strip():
                                early_stop_reason='AP95 host single-step whitelist/hold/visual authorization rejected before any guest write';break
                            qmp('stop');host_step+=1;input_gate.command(host_step,key,hold_ms,description,reason_text);qmp('cont')
                        elif proposed.get('step',0)>host_step+1:
                            early_stop_reason='AP95 out-of-order host single-step command';break
                if 'FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN' in serial_now and 'FX3_FILE100_NATIVE_FILE_READ generation=1 ' in serial_now and not replay_input_verified:
                    qmp('stop')
                    before_AP='FX3_AP_NATURAL_BOOTIN_BEGIN' not in serial_now
                    input_path=run/'backup-native-load-before-AP.bin'
                    qmp('human-monitor-command',{'command-line':'pmemsave 0x404000000 0x221000 "'+str(input_path)+'"'})
                    raw=input_path.read_bytes();native=native_seed.read_bytes();parts=[]
                    for off in [0,0xd2000]:
                        n=sum(struct.unpack_from('<2I',native,off+24));loaded=raw[off:off+n];filepart=native[off:off+n]
                        checksum=(sum(loaded)-sum(loaded[32:36]))&0xffffffff
                        different=[i for i,(x,y) in enumerate(zip(loaded,filepart)) if x!=y]
                        parts.append({'offset':off,'native_file_bytes':n,'loaded_sha256':hashlib.sha256(loaded).hexdigest(),'file_sha256':hashlib.sha256(filepart).hexdigest(),'all_bytes_equal':loaded==filepart,'payload_after_header_equal':loaded[256:]==filepart[256:],'difference_count':len(different),'first_difference_offsets':different[:64],'loaded_first64_hex':loaded[:64].hex(),'loaded_checksum_valid':checksum==struct.unpack_from('<I',loaded,32)[0]})
                    file_receipt=capture_native_file(qmp,run,'native-load-before-AP')
                    verified=before_AP and 'FX3_BACKUP_INSMOD_RC=0' in serial_now and file_receipt.get('valid') and file_receipt.get('sha256')==candidate['native_Backup_seed']['sha256']
                    proof={'method':'Original backup.ko Backup_load=1, native insmod return and actual source file SHA; QMP read-only bank snapshot after load, no RAM replay','path':str(input_path),'sha256':digest(input_path),'before_AP_bootin_marker':before_AP,'file_sha256':candidate['native_Backup_seed']['sha256'],'native_file_seen_and_module_load0':verified,'native_file_O_RDONLY_readback':file_receipt,'bank_comparison':parts,'force02cf0014':raw[0x8eb51],'force01070140':raw[0x6e7ac],'date02cf01b4':raw[0x9100c],'no_RAM_replay_helper':True}
                    (run/'ap102-native-load-readback.json').write_text(json.dumps(proof,indent=2)+'\n')
                    if not verified:
                        early_stop_reason='AP101 original file/load/preAP identity gate failed';break
                    replay_input_verified=True
                    qmp('cont')
                seen_uptime=list(re.finditer(r'FX3_GUEST_UPTIME_SNAPSHOT\s*\n([0-9]+\.[0-9]+) ([0-9]+\.[0-9]+)',serial_now))
                for index,match in enumerate(seen_uptime):
                    if index>=len(uptime_samples):
                        uptime_samples.append({'sample':index+1,'guest_proc_uptime_seconds':float(match.group(1)),'guest_idle_seconds':float(match.group(2)),'host_elapsed_first_observed_seconds':time.monotonic()-guest_start,'scope':'Actual existing guest cat /proc/uptime; host first-observed timestamp includes polling and QMP pauses, not printk time'})
                        (run/'guest-uptime-samples.json').write_text(json.dumps(uptime_samples,indent=2)+'\n')
                if any(x in serial_now for x in ['FX3_OSD_PAIR_DEADLINE_EVIDENCE_END','FX3_OSD_ALLOC_DEADLINE_EVIDENCE_END','FX3_OSD_HEADLESS_REJECT','FX3_BACKUP_CP_OWNER_FAILED','FX3_AP89_REPLAY_FAILED','FX3_MEDIA_OWNED_RAW_REJECT','FX3_MEDIA_BIND_REJECT','FX3_GPE_RESOURCE_BIND_REJECT','FX3_PRESET_CONTEXT_BIND_REJECT','FX3_GPE_EARLY_BIND_REJECT','FX3_BACKUP_CP_REJECT','FX3_BACKUP_CP_RETRY','FX3_SYS_UUD_REJECT','FX3_DISPLAY_BIND_FAIL','FX3_DISPLAY_SELFTEST_FAIL']):
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
                if not kernel_observer.points:time.sleep(.25)
            if p.poll() is None:
                qmp('stop')
                kernel_observer.close()
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
                native_file_reads.append(capture_native_file(qmp,run,'final-before-shutdown'))
                (run/'ap102-native-file-readbacks.json').write_text(json.dumps(native_file_reads,indent=2)+'\n')
                shutdown={'observation_complete':True,'serial_bytes_before_cleanup':(run/'serial.log').stat().st_size,'cleanup_is_after_acceptance_window':True}
                (run/'ap102-cleanup-phase.json').write_text(json.dumps(shutdown,indent=2)+'\n')
                if input_gate is not None:
                    restoration103=restore_native_api(qmp,input_gate,run,timeout=20)
                    shutdown['restore103_passed']=restoration103['passed']
                    shutdown['restore103_reason']=restoration103['reason']
                    (run/'ap102-cleanup-phase.json').write_text(json.dumps(shutdown,indent=2)+'\n')
                    native_file_reads.append(capture_native_file(qmp,run,'after-restore-check'))
                    (run/'ap102-native-file-readbacks.json').write_text(json.dumps(native_file_reads,indent=2)+'\n')
                    if not restoration103['passed']:error='AP103 native API restoration not acknowledged/verified: '+restoration103['reason']
                qmp('query-status')
                qmp('query-cpus-fast')
                qmp('quit')
            p.wait(timeout=5)
        except (Exception, KeyboardInterrupt) as exc:
            error = repr(exc)
        finally:
            os.chdir(previous_cwd)
            if p is not None and p.poll() is None and qmp is not None:
                recovery102={}
                try:
                    qmp('stop')
                    if kernel_observer is not None:
                        try:kernel_observer.close()
                        except Exception as bp_close_exc:recovery102['breakpoint_cleanup_error']=repr(bp_close_exc)
                    if input_gate is not None and not (run/'restore103-receipt.json').exists():
                        recovery102['restore103']=restore_native_api(qmp,input_gate,run,timeout=20)
                    qmp('quit');p.wait(timeout=5);recovery102['qemu_quit_reaped']=True
                except Exception as cleanup_exc:recovery102['error']=repr(cleanup_exc)
                (run/'ap102-emergency-cleanup.json').write_text(json.dumps(recovery102,indent=2)+'\n')
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
    if (run/'ap105-observations.json').exists():
        receipt['AP105_observation']=json.loads((run/'ap105-observations.json').read_text())
    if (run/'restore103-receipt.json').exists():
        receipt['restore103']=json.loads((run/'restore103-receipt.json').read_text())
        if not receipt['restore103']['passed'] and error is None:
            error='AP103 native API restoration failed';receipt['host_observer_error']=error
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
