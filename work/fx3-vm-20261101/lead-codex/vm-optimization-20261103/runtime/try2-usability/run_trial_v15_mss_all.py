#!/usr/bin/env python3
"""TRY2 local web runner for the validated English, performance, and readiness candidate."""
from pathlib import Path
import sys
sys.path.insert(1, str(Path(__file__).resolve().parents[4] / "menu-repair-01/runtime"))
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
from trial_ring_usability import TrialRingReader
from trial_web_v3_usability import TrialState, start_server, KEYS
from trial_log_v4_mss import FullLogMonitor
from trial_health_v2 import evaluate as evaluate_health
from gate_input_usability import InputGate,valid_command
from file_readback100 import capture as capture_native_file
from restore_api103_v2 import restore_native_api

ROOT = Path(__file__).resolve().parents[4] / "menu-repair-01/runtime"
OUT = Path(__file__).resolve().parent
BASE = ROOT.parent
FROZEN = Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm')
VOLUME_UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def classify_internal_review(request, observed, frame, run_id, next_step,
                             current_png_sha, observed_png_sha, rejected):
    """Reject a stale visual decision without consuming a guest input step."""
    if (request.get('mode') != 'internal-hoststep-v1' or request.get('key') not in KEYS
            or request.get('hold_ms') != 100
            or not isinstance(request.get('observed_page'), str) or not request['observed_page'].strip()
            or not isinstance(request.get('reason'), str) or not request['reason'].strip()):
        raise RuntimeError('内部逐键请求格式、白名单或100ms合同无效')
    if request.get('run_id') != run_id:
        return 'stale', 'wrong_run_id'
    if request.get('step') != next_step:
        return 'stale', 'step_out_of_sequence'
    identity = (next_step, request.get('observed_sequence'), request.get('observed_png_sha256'))
    if identity in rejected:
        return 'stale', 'previously_rejected_visual_identity'
    if observed is None:
        return 'stale', 'observed_frame_missing'
    if (request.get('observed_sequence') != observed.get('sequence')
            or request.get('observed_png_sha256') != observed.get('PNG_sha256')):
        return 'stale', 'observed_frame_replaced'
    if observed_png_sha != observed.get('PNG_sha256'):
        raise RuntimeError('已审阅PNG的文件字节与记录哈希不符')
    if (frame is None or observed['sequence'] > frame['sequence']
            or observed['PNG_sha256'] != frame['PNG_sha256']
            or current_png_sha != frame['PNG_sha256']):
        return 'stale', 'current_committed_frame_changed'
    return 'accept', None


def input_check(item):
    p = Path(item['path'])
    if not p.is_file() or p.is_symlink() or digest(p) != item['sha256']:
        raise RuntimeError('Input SHA/path mismatch: ' + str(p))
    return p


def checkpoint(value):
    path = OUT / 'mss-all-STATE.json'
    state = json.loads(path.read_text()) if path.exists() else {}
    state.update(value)
    state['schema'] = 'fx3-menu-repair-runtime-checkpoint-v1'
    state['owner'] = 'try2-usability'
    state['updated_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    temp = OUT / 'mss-all-STATE.json.tmp'
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def main():
    ap = argparse.ArgumentParser(description='FX3 固件菜单本机试用')
    ap.add_argument('--port', type=int, default=8765, help='127.0.0.1 本地端口，默认8765')
    ap.add_argument('--max-minutes', type=int, default=15, help='本轮诊断上限，1..15分钟；默认15分钟')
    ap.add_argument('--max-steps', type=int, default=32, help='底层协议容量固定32；诊断实际最多12键')
    ap.add_argument('--internal-hoststep', action='store_true', help='内部逐键文件门；不启动网页服务，不构成浏览器验收')
    ap.add_argument('--exit-at-phase', choices=['pre-bind', 'bound-before-first-frame'], help='有界退出边界验证')
    ns = ap.parse_args()
    if not 0 <= ns.port <= 65535 or not 1 <= ns.max_minutes <= 15 or ns.max_steps != 32 or not ns.internal_hoststep:
        ap.error('本版只允许内部逐键诊断：端口0..65535，会话1..15分钟，底层协议容量32，实际最多12键')
    if not valid_command(1, 0x1ab, 100, 0, 0, ns.max_steps) or not valid_command(12, 0x30, 100, 11, 0, ns.max_steps):
        raise RuntimeError('InputGate capacity contract rejected before QEMU startup')
    ns.candidate = OUT/'vmopt-20261103-try2-mss-all-v3/candidate.json'
    ns.seconds = ns.max_minutes*60
    ns.trace_seconds = 0
    ns.icount_shift = None
    ns.smp = 4
    ns.tcg_thread = 'multi'
    ns.label = 'try2mssallinternal' if ns.internal_hoststep else 'disabled'
    vol = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    if vol.get('VolumeUUID') != VOLUME_UUID:
        raise RuntimeError('External volume UUID mismatch')
    candidate_path = ns.candidate.resolve()
    if not candidate_path.is_relative_to(OUT / 'vmopt-20261103-try2-mss-all-v3'):
        raise RuntimeError('Candidate manifest must be in this menu-repair task')
    if digest(candidate_path) != '2382063eacb5f185e8553c2596be2c644654efe7234adc1e4578f7464ab99a05':
        raise RuntimeError('TRY2 manifest identity changed')
    candidate = json.loads(candidate_path.read_text())
    if candidate.get('try2_contract', {}).get('ready_before_CP_binding') is not True:
        raise RuntimeError('TRY2 readiness contract missing')
    if digest(Path(candidate['try2_contract']['base'])) != candidate['try2_contract']['base_sha256']:
        raise RuntimeError('TRY2 cold-reload base identity changed')
    native_seed=input_check(candidate['native_Backup_seed'])
    baseline = json.loads((FROZEN / 'manifest.json').read_text())
    checks = [(FROZEN / rel, h) for rel, h in baseline['runtime_sha256'].items()]
    checks.append((Path(baseline['kernel']['path']), baseline['kernel']['sha256']))
    checks.append((native_seed,candidate['native_Backup_seed']['sha256']))
    for p, h in checks:
        input_check({'path': str(p), 'sha256': h})
    dtb = input_check(candidate['dtb'])
    initrd = input_check(candidate['initrd'])
    if not dtb.resolve().is_relative_to(OUT / 'vmopt-20261103-try2-mss-all-v3') or not initrd.resolve().is_relative_to(OUT / 'vmopt-20261103-try2-mss-all-v3'):
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
            snapshots.append({'address':address,'size':256,'name':'ap101-control-final.bin','scope':'Read-only final hoststep command/done header'})
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
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close()
            for held in locks:
                fcntl.flock(held, fcntl.LOCK_UN); held.close()
            raise RuntimeError('已有 FX3 试用或验证正在运行，请等待其结束后重试。不会抢锁或停止其他会话。')
        locks.append(lock)
    label = ''.join(c for c in ns.label if c.isalnum() or c in '-_')[:32]
    (OUT / 'runs').mkdir(exist_ok=True)
    run = OUT / 'runs' / (label + '-' + uuid.uuid4().hex[:8])
    run.mkdir()
    run.chmod(0o700)
    observer_dir = run / 'observer-source'
    observer_dir.mkdir()
    observer_sources = []
    for name in [Path(__file__).name, 'cpio_audit.py', 'decode_printk_ring.py', 'osd_ring93_v4.py','gate_input_usability.py','file_readback100.py','trial_web_v3_usability.py','trial_ring_usability.py','trial_log_v4_mss.py','restore_api103_v2.py']:
        shutil.copyfile(OUT / name if (OUT / name).exists() else ROOT / name, observer_dir / name)
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
        resource.setrlimit(resource.RLIMIT_FSIZE, (512 * 1024 * 1024, 512 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    trial = TrialState(run, ns.seconds, ns.max_steps)
    server = web_thread = None
    qmp = None
    input_gate = None
    ring_reader = None
    s = f = None
    native_file_reads = []
    step_captures = []
    shutdown = {'attempted': False, 'API16_restored': False, 'quit_sent': False}
    stop_cause = None
    log_monitor = FullLogMonitor(run/'serial.log', candidate.get('required_markers', []))

    def terminated(signum, frame):
        nonlocal stop_cause
        stop_cause = 'Ctrl-C' if signum == signal.SIGINT else 'SIGTERM'
        trial.update(ready=False, phase='stopping', message='正在结束试用并回收资源…')
        trial.stop.set()

    signal.signal(signal.SIGTERM, terminated)
    signal.signal(signal.SIGINT, terminated)

    with (run / 'host-stdout.log').open('wb') as stdout, (run / 'host-stderr.log').open('wb') as stderr:
        try:
            if not ns.internal_hoststep:
                server, web_thread = start_server(trial, ns.port)
            p = subprocess.Popen(args, cwd=run, env=env, stdout=stdout, stderr=stderr,
                                 start_new_session=True, preexec_fn=limits)
            checkpoint({'phase': 'TRY2_RUNNING_LOCAL_INTERACTIVE', 'current_candidate': str(candidate_path),
                        'current_candidate_sha256': digest(candidate_path), 'current_run': str(run),
                        'fixed_inputs': [{'path': str(p), 'sha256': h} for p, h in checks],
                        'guest_process': {'pid': p.pid, 'current_running_pid': p.pid,
                                          'observer_pid': os.getpid(), 'exit': None, 'reaped': False},
                        'locks': [{'path': str(FROZEN / '.run.lock'), 'holder': os.getpid(), 'status': 'held'},
                                  {'path': str(ROOT / '.run.lock'), 'holder': os.getpid(), 'status': 'held'}],
                        'next_minimal_command': {'status': '本机交互试用运行中', 'argv': [sys.executable, str(Path(__file__)), '--port', str(ns.port)]}})
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
            ring_reader = TrialRingReader(run, qmp, trial)
            input_gate = InputGate(run, delete_key=0x1f8, max_steps=ns.max_steps)
            (run/'trial-session.json').write_text(json.dumps({
                'url': trial.url, 'run': str(run), 'observer_pid': os.getpid(), 'qemu_pid': p.pid,
                'authority': 'TRY2 usability', 'max_seconds': ns.seconds, 'max_steps': ns.max_steps,
                'exit_at_phase': ns.exit_at_phase,
                'models_identical_to_frozen_AP101_r4': False, 'listen': '127.0.0.1',
                'button_whitelist': {hex(k): v for k, v in KEYS.items()},
                'hold_ms': 100, 'HTTP_threads_have_no_QMP_or_guest_access': True,
            }, ensure_ascii=False, indent=2)+'\n')
            checkpoint({'trial_url': trial.url, 'trial_run': str(run)})
            if trial.url:
                print('试用网址:', trial.url, flush=True)
            else:
                print('内部逐键文件门，不启动网页服务。', flush=True)
            print('RUN', run, flush=True)
            print('等待固件待机画面；结束请用网页按钮或 Ctrl-C。', flush=True)
            guest_start = time.monotonic()
            deadline = guest_start + ns.seconds
            trial.deadline = deadline
            replay_input_verified = False
            phaseA_capture = None
            shutdown_count_at_ready = 0
            power_off_count_at_ready = 0
            last_screen_count = 0
            last_screen_observed_at = guest_start
            host_step = 0
            rejected_visual_identities = set()
            current_command = None
            up_seen = {}
            last_ring_poll = 0
            last_metrics = 0
            next_native_file = guest_start+20
            next_frame_wait = guest_start+120

            phase_exit_hit = False
            while time.monotonic() < deadline and p.poll() is None and not trial.stop.is_set():
                if ns.internal_hoststep and current_command is None and host_step >= 12:
                    stop_cause = 'diagnostic_actual_step_limit_12'
                    break
                if ns.internal_hoststep and time.monotonic() >= deadline-240:
                    stop_cause = 'internal_input_window_end_with_240s_cleanup_reserve'
                    break
                serial_now = log_monitor.poll()
                if ns.exit_at_phase == 'pre-bind' and 'FX3_SYNC100_BACKEND_BOUND' not in serial_now:
                    phase_exit_hit = True; stop_cause = 'pre_bind_exit_phase'; break
                if (ns.exit_at_phase == 'bound-before-first-frame'
                        and 'FX3_SYNC100_BACKEND_BOUND' in serial_now and ring_reader.last == 0):
                    phase_exit_hit = True; stop_cause = 'bound_before_first_frame_exit_phase'; break
                if log_monitor.failure:
                    early_stop_reason = log_monitor.failure
                    trial.fail(early_stop_reason)
                    break
                if log_monitor.native_power_off_events:
                    early_stop_reason = 'native_model_power_off_observed: ' + log_monitor.native_power_off_events[-1]
                    trial.fail(early_stop_reason)
                    # No more input. Let the preallocated passive observer export its two records.
                    flush_deadline = min(deadline, time.monotonic()+0.5)
                    while time.monotonic() < flush_deadline:
                        if 'FX3_POWER_NATIVE_NOTIFY seq=2' in log_monitor.poll():
                            break
                        time.sleep(.02)
                    break
                if phaseA_capture is not None and len(log_monitor.native_shutdown_events) > shutdown_count_at_ready:
                    early_stop_reason = 'native_shutdown_after_ready_without_user_power_key: ' + log_monitor.native_shutdown_events[-1]
                    trial.fail(early_stop_reason)
                    break
                if phaseA_capture is not None and len(log_monitor.native_power_off_events) > power_off_count_at_ready:
                    early_stop_reason = 'native_model_power_off_after_ready_without_user_power_key: ' + log_monitor.native_power_off_events[-1]
                    trial.fail(early_stop_reason)
                    break
                if log_monitor.offset > 480*1024*1024:
                    stop_cause = 'serial_log_safety_limit'
                    break
                if (run/'STOP_FOR_REVIEW').exists():
                    early_stop_reason = (run/'STOP_FOR_REVIEW').read_text()
                    trial.fail(early_stop_reason)
                    break
                if time.monotonic()-last_ring_poll >= .4:
                    ring_reader.poll()
                    last_ring_poll = time.monotonic()
                    if phaseA_capture is not None and trial.black_after_ready:
                        early_stop_reason = 'render: native committed all-zero pixels after ready; legitimate black/sleep semantics unknown'
                        trial.fail(early_stop_reason)
                        break
                if time.monotonic() >= next_native_file:
                    qmp('stop')
                    native_file_reads.append(capture_native_file(qmp, run, 'periodic-%02d' % len(native_file_reads)))
                    qmp('cont')
                    next_native_file = time.monotonic()+60

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
                    (run/'ap101-native-load-readback.json').write_text(json.dumps(proof,indent=2)+'\n')
                    if not verified:
                        raise RuntimeError('Original file/load/preAP identity gate failed')
                    replay_input_verified=True
                    qmp('cont')

                opens = list(re.finditer(r'FX3_AP89_SCREEN_OPEN_ENTER [^\n]*id2=(0x[0-9a-f]+)', serial_now))
                if len(opens) != last_screen_count:
                    last_screen_count = len(opens)
                    last_screen_observed_at = time.monotonic()
                if phaseA_capture is None and replay_input_verified and opens and ring_reader.current_record and time.monotonic()-last_screen_observed_at >= 10:
                    branches = re.findall(r'FX3_MEDIA_START_BRANCH [^\n]*state=(\d+)', serial_now)
                    notify = re.findall(r'FX3_MEDIA_NOTIFY [^\n]*mediaID=(0x[0-9a-f]+) [^\n]*status=(\d+)', serial_now)
                    freed = re.findall(r'FX3_RM_NATIVE_FREE [^\n]*bytes=(\d+) [^\n]*result=0 ', serial_now)
                    valid = (branches == ['2', '2'] and sorted(notify) == [('0x1000', '0'), ('0x1010', '0')]
                             and all(str(n) in freed for n in (136, 28, 7)) and 'FX3_KEY96_READY' in serial_now
                             and 'FRONT_FULL_BODY' in serial_now and 'raw=02000007000000 ' in serial_now
                             and opens[-1][1] not in ('0x2ae', '0x2af', '0x2c7')
                             and ring_reader.current_record['nonuniform_pixels'])
                    if valid:
                        phaseA_capture = ring_reader.evidence('standby-ready')
                        shutdown_count_at_ready = len(log_monitor.native_shutdown_events)
                        power_off_count_at_ready = len(log_monitor.native_power_off_events)
                        (run/'trial-phaseA.json').write_text(json.dumps({
                            'branches': branches, 'native_notifications': notify, 'native_free_sizes': freed,
                            'last_native_screen': opens[-1][1], 'no_keys_before_ready': not input_gate.history,
                            'native_file_load_verified': True, 'QMP': phaseA_capture,
                        }, ensure_ascii=False, indent=2)+'\n')
                        trial.update(phase='ready', ready=True, message='固件已就绪。按 MENU 打开菜单。')
                if phaseA_capture is None and time.monotonic() > next_frame_wait:
                    trial.update(message='固件仍在启动，请稍候；首次进入界面可能需要几分钟。')
                    next_frame_wait = time.monotonic()+120

                for match in re.finditer(r'FX3_SYNTH_KEY step=(\d+) key=(0x[0-9a-f]+) status=0 [^\n]*result=0 ', serial_now):
                    up_seen.setdefault(int(match[1]), (time.monotonic(), int(match[2], 0)))
                frame_changed = (current_command is not None and ring_reader.current_record is not None
                                 and ring_reader.current_record.get('PNG_sha256') != current_command['before_command_png_sha256'])
                both_native_events = (current_command is not None and all(
                    re.search(r'FX3_KEY_INPUT_RECV step=%d key=%s status=%d [^\n]*native_result=0' % (host_step, hex(current_command['key']), status), serial_now)
                    for status in (0, 1)))
                unchanged_wait = 180 if current_command is not None and current_command['key'] == 0x1ab else 6
                if (current_command is not None and host_step in up_seen and both_native_events
                        and time.monotonic()-up_seen[host_step][0] >= 1
                        and (frame_changed or time.monotonic()-up_seen[host_step][0] >= unchanged_wait)):
                    captured = ring_reader.evidence('step-%02d-key-%03x' % (host_step, current_command['key']), host_step, current_command['key'])
                    if captured.get('error'):
                        raise RuntimeError('按键后未取得已校验提交帧')
                    step_captures.append(captured)
                    (run/'trial-step-readbacks.json').write_text(json.dumps(step_captures, ensure_ascii=False, indent=2)+'\n')
                    with trial.lock:
                        trial.events.append('%02d · %s · 固件已接收，帧 %s%s' % (host_step, current_command['label'], captured['sequence'], '' if frame_changed else '（画面未变）'))
                        trial.busy = False
                    current_command = None
                    trial.update(message='固件提交全黑画面，已暂停按键；可结束试用。' if not trial.render_valid
                                 else '本轮已达按键上限，请结束后重新启动。' if host_step == ns.max_steps
                                 else '画面已更新，可以继续操作。' if frame_changed
                                 else '按键已接收，像素未变；请观察后再继续。')
                if current_command is not None and host_step not in up_seen and time.monotonic()-current_command['sent_monotonic'] > 12:
                    raise RuntimeError('按键 12 秒内未得到原生 key-up 回执')

                proposed = trial.take() if current_command is None and not ns.internal_hoststep else None
                if ns.internal_hoststep and current_command is None and phaseA_capture is not None and trial.render_valid:
                    request_path = run/'INTERNAL_STEP.json'
                    if request_path.exists():
                        if request_path.is_symlink() or request_path.stat().st_size > 4096:
                            raise RuntimeError('内部逐键请求文件身份/大小无效')
                        request = json.loads(request_path.read_text())
                        frame = ring_reader.current_record
                        observed_path = run/('internal-observe-%02d.json' % (host_step+1))
                        observed = json.loads(observed_path.read_text()) if observed_path.is_file() else None
                        reviewed_png = run/('internal-observe-%02d.png' % (host_step+1))
                        status, stale_reason = classify_internal_review(
                            request, observed, frame, run.name, host_step+1,
                            digest(run/'trial-frame.png'), digest(reviewed_png) if reviewed_png.is_file() else None,
                            rejected_visual_identities)
                        if status == 'stale':
                            rejected_visual_identities.add((request.get('step'), request.get('observed_sequence'),
                                                            request.get('observed_png_sha256')))
                            suffix = uuid.uuid4().hex[:8]
                            stale_base = 'internal-stale-%02d-%s' % (host_step+1, suffix)
                            request_path.rename(run/(stale_base+'-request.json'))
                            shutil.copy2(run/'trial-frame.png', run/(stale_base+'-current.png'))
                            (run/(stale_base+'-current.json')).write_text(json.dumps(frame, ensure_ascii=False, indent=2)+'\n')
                            (run/(stale_base+'.json')).write_text(json.dumps({
                                'status':'stale_no_guest_write', 'reason':stale_reason,
                                'run_id':run.name, 'next_step_unchanged':host_step+1,
                                'sent_steps_unchanged':host_step,
                                'current_png':str(run/(stale_base+'-current.png')),
                                'current_png_sha256':frame['PNG_sha256'] if frame else None,
                                'new_human_review_required':True,
                                'old_request_never_auto_retried':True}, ensure_ascii=False, indent=2)+'\n')
                            trial.update(message='看图后画面已变化；旧请求未发键，请查看新的PNG再决定。')
                        else:
                            request_path.rename(run/('internal-step-%02d-request.json' % (host_step+1)))
                            proposed = {'key': request['key'], 'label': KEYS[request['key']],
                                        'observed_frame': dict(observed), 'observed_page': request['observed_page'],
                                        'reason': request['reason'], 'requested_monotonic': time.monotonic(),
                                        'source': 'internal_hoststep_file'}
                if proposed is not None and not trial.stop.is_set():
                    # Inspect ALL bytes appended since this iteration began before any guest write.
                    log_monitor.poll()
                    if log_monitor.failure:
                        early_stop_reason = log_monitor.failure
                        trial.fail(early_stop_reason)
                        break
                    key = proposed['key']
                    if not valid_command(host_step+1, key, 100, host_step, input_gate.delete_key, ns.max_steps):
                        raise RuntimeError('白名单、步数或按键持续时间校验失败')
                    frame = proposed['observed_frame']
                    description = ('内部看图：'+proposed['observed_page'] if ns.internal_hoststep else '用户网页显示本轮原生提交帧') + ' sequence=%d SHA256=%s' % (frame['sequence'], frame['PNG_sha256'])
                    reason_text = proposed['reason'] if ns.internal_hoststep else '用户点击网页按钮：'+proposed['label']
                    qmp('stop')
                    host_step += 1
                    sent = input_gate.command(host_step, key, 100, description, reason_text)
                    qmp('cont')
                    current_command = dict(proposed, step=host_step, before_command_sequence=ring_reader.last,
                                           before_command_png_sha256=ring_reader.current_record['PNG_sha256'], sent_monotonic=time.monotonic())
                    with (run/'trial-input-events.jsonl').open('a') as events:
                        events.write(json.dumps(dict(current_command, gate=sent), ensure_ascii=False)+'\n')
                    trial.update(steps=host_step, message='按键已发送，等待固件画面…')

                if time.monotonic()-last_metrics >= 5:
                    st = subprocess.run(['ps', '-o', 'rss=,vsz=', '-p', str(p.pid)], capture_output=True, text=True)
                    samples.append({'elapsed_seconds': time.monotonic()-start, 'rss_vsz_kib': st.stdout.strip()})
                    last_metrics = time.monotonic()
                time.sleep(.05)
            if ns.exit_at_phase and not phase_exit_hit:
                early_stop_reason = 'requested exit phase not observed'
                trial.fail(early_stop_reason)
            if stop_cause is None:
                stop_cause = 'health_failure' if early_stop_reason else ('end_trial_button' if trial.stop.is_set() else 'maximum_duration' if p.poll() is None else 'qemu_exited')
        except (Exception, KeyboardInterrupt) as exc:
            error = repr(exc)
            stop_cause = 'host_error'
            trial.fail(error)
        finally:
            os.chdir(previous_cwd)
            trial.update(ready=False, phase='stopping', message='正在恢复原 API、退出模拟器并回收资源…')
            trial.stop.set()
            if p is not None and p.poll() is None and qmp is not None:
                # Cleanup runs for HTTP end, Ctrl-C, timeout, and observation errors alike.
                shutdown['attempted'] = True
                try:
                    qmp('stop')
                    if ring_reader is not None:
                        ring_reader.poll(final=True)
                        if ring_reader.current_record:
                            ring_reader.evidence('final')
                        ring_reader.save()
                    for snapshot in snapshots:
                        qmp('human-monitor-command', {'command-line': 'pmemsave '+hex(snapshot['address'])+' '+hex(snapshot['size'])+' "'+str(run/snapshot['name'])+'"'})
                    shutdown['serial_bytes_before_cleanup'] = (run/'serial.log').stat().st_size
                except Exception as exc:
                    shutdown['snapshot_error'] = repr(exc)
                try:
                    log_monitor.poll()
                    if 'FX3_FILE100_OBSERVER_READY' in '\n'.join(log_monitor.selected):
                        native_file_reads.append(capture_native_file(qmp, run, 'final-before-shutdown'))
                    restore = restore_native_api(qmp, input_gate, run, timeout=20)
                    shutdown['restore103'] = restore
                    shutdown['API16_restored'] = restore['passed']
                    shutdown['native_unbind_return'] = 0 if restore['reason'] in ('guest_acknowledged_and_original_bytes_verified', 'already_original_no_request_no_resume') else None
                    if not restore['passed']:
                        shutdown['restore_error'] = restore['reason']
                except Exception as exc:
                    shutdown['restore_error'] = repr(exc)
                try:
                    qmp('quit')
                    shutdown['quit_sent'] = True
                except Exception as exc:
                    shutdown['quit_error'] = repr(exc)
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            if p is not None and p.poll() is None:
                os.killpg(p.pid, signal.SIGTERM)
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait(timeout=3)
            for stream in (f, s, input_gate.sock if input_gate else None):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass

    log_monitor.poll()
    (run/'qmp.json').write_text(json.dumps(journal, ensure_ascii=False, indent=2)+'\n')
    (run/'trial-native-file-readbacks.json').write_text(json.dumps(native_file_reads, indent=2)+'\n')
    (run/'trial-cleanup-phase.json').write_text(json.dumps(shutdown, ensure_ascii=False, indent=2)+'\n')
    unchanged = all(path.is_file() and digest(path) == h for path, h in checks)
    try:
        os.kill(p.pid, 0)
        pid_absent = False
    except (ProcessLookupError, AttributeError):
        pid_absent = True
    for lock in locks:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    lock_status = []
    for path in (FROZEN/'.run.lock', ROOT/'.run.lock'):
        with path.open('rb') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                free = True
                fcntl.flock(lock, fcntl.LOCK_UN)
            except BlockingIOError:
                free = False
            lock_status.append({'path': str(path), 'free_at_close': free})
    lifecycle_pass = (p is not None and p.returncode == 0 and pid_absent and unchanged
                      and all(x['free_at_close'] for x in lock_status)
                      and shutdown.get('API16_restored') and shutdown.get('native_unbind_return') == 0
                      and shutdown.get('quit_sent'))
    protocol_pass, render_pass, health_pass = evaluate_health(
        lifecycle=lifecycle_pass, observer_error=error, serial_failure=log_monitor.failure,
        markers_complete=phase_exit_hit if ns.exit_at_phase else all(log_monitor.markers.values()),
        standby_observed=phaseA_capture is not None, render_valid=trial.render_valid,
        black_after_ready=trial.black_after_ready, early_stop=early_stop_reason)
    receipt = {'created_utc': started, 'duration_seconds': time.monotonic()-start,
               'candidate': str(candidate_path), 'candidate_sha256': digest(candidate_path),
               'models_identical_to_frozen_AP101_r4': False, 'authority': 'msg_3a52a0ab7e46',
               'observer_source_snapshot': observer_sources, 'run': str(run),
               'maximum_seconds': ns.seconds, 'maximum_steps': ns.max_steps, 'diagnostic_actual_step_limit': 12, 'stop_cause': stop_cause,
               'internal_hoststep_mode': ns.internal_hoststep, 'HTTP_key_source_used': not ns.internal_hoststep,
               'qemu_pid': None if p is None else p.pid, 'qemu_exit': None if p is None else p.returncode,
               'process_reaped': p is not None and p.poll() is not None, 'PID_absent': pid_absent,
               'inputs_unchanged': unchanged, 'input_checks': [{'path': str(path), 'sha256': h} for path, h in checks],
               'locks': lock_status, 'host_observer_error': error, 'memory_samples': samples,
               'early_stop_reason': early_stop_reason, 'full_serial_bytes_inspected': log_monitor.offset,
               'serial_health_failure': log_monitor.failure, 'markers': log_monitor.markers,
               'marker_evidence': log_monitor.marker_evidence,
               'date99_raw_serial_evidence': log_monitor.date99_raw_receipt(),
               'cleanup': shutdown, 'lifecycle_pass': bool(lifecycle_pass),
               'protocol_pass': protocol_pass, 'render_pass': render_pass,
               'black_frame_semantics': 'unknown; an all-zero committed panel cannot satisfy this visual trial',
               'native_shutdown_after_ready': bool(phaseA_capture is not None and len(log_monitor.native_shutdown_events) > shutdown_count_at_ready),
               'native_shutdown_original_lines': log_monitor.native_shutdown_events,
               'native_shutdown_count_at_ready': shutdown_count_at_ready if 'shutdown_count_at_ready' in locals() else None,
               'native_model_power_off_after_ready': bool(phaseA_capture is not None and len(log_monitor.native_power_off_events) > power_off_count_at_ready),
               'native_model_power_off_original_lines': log_monitor.native_power_off_events,
               'native_model_power_off_count_at_ready': power_off_count_at_ready if 'power_off_count_at_ready' in locals() else None,
               'health_pass': health_pass,
               'requested_exit_phase': ns.exit_at_phase, 'requested_exit_phase_hit': phase_exit_hit if 'phase_exit_hit' in locals() else False,
               'key_steps': trial.steps, 'step_captures': step_captures,
               'standby_ready': phaseA_capture is not None if 'phaseA_capture' in locals() else False,
               'menu_verified': False, 'visual_acceptance_separate_from_health': True,
               'render_valid_at_end': trial.render_valid, 'black_after_ready': trial.black_after_ready,
               'render_observation_ok': bool(phaseA_capture is not None and trial.render_valid and not trial.black_after_ready),
               'browser_visual_acceptance': None,
               'physical_device_operations': 0, 'remote_network_connections': 0, 'HTTP_loopback_only': True,
               'scope': 'TRY2 original FX3 menu software model with improved icon and focus presentation; no camera, live view, or exact compositor claim'}
    (run/'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    checkpoint({'phase': 'TRY2_COMPLETE_HEALTHY' if health_pass else 'TRY2_COMPLETE_REVIEW_PENDING',
                'last_run': str(run), 'current_run': None, 'last_run_immutable': True,
                'guest_process': {'pid': receipt['qemu_pid'], 'current_running_pid': None,
                                  'observer_pid': os.getpid(), 'exit': receipt['qemu_exit'], 'reaped': receipt['process_reaped']},
                'inputs_unchanged': unchanged, 'trial_url': None,
                'locks': [{'path': x['path'], 'holder': None, 'status': 'released' if x['free_at_close'] else 'held_by_other'} for x in lock_status],
                'TRY2': {'health_pass': health_pass, 'last_run': str(run), 'launch': [sys.executable, str(Path(__file__))]}})
    trial.update(phase='finished', busy=False, result={'health_pass': health_pass, 'qemu_exit': receipt['qemu_exit'],
                                                    'API16_restored': shutdown.get('API16_restored')},
                 message='试用已结束，模拟器已退出，资源已回收。' if lifecycle_pass else '试用已结束，收尾检查未全部通过，请查看启动终端。',
                 error=trial.error or early_stop_reason or log_monitor.failure or error)
    print('回执:', run/'receipt.json', flush=True)
    print('HEALTH', health_pass, 'QEMU_EXIT', receipt['qemu_exit'], 'REAPED', receipt['process_reaped'],
          'API16_RESTORED', shutdown.get('API16_restored'), 'INPUTS_UNCHANGED', unchanged, flush=True)
    if server is not None:
        time.sleep(2)
        server.shutdown()
        server.server_close()
        web_thread.join(timeout=2)
    return 0 if health_pass else 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print('Stopped:', exc, file=sys.stderr)
        sys.exit(2)
