#!/usr/bin/env python3
"""Bounded FX6 AP load observer on fixed FX3 VM; only runtime owner may run."""
import datetime
import fcntl
import hashlib
import json
import os
import plistlib
import re
import resource
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAC = HERE.parents[5]
FX3 = MAC / 'work/fx3-vm-20261101'
RUNTIME = FX3 / 'lead-codex/vm-optimization-20261103/runtime'
BASE = RUNTIME / 'try2-usability/fx3-platform-frozen-baseline.json'
DONOR = MAC / 'work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor'
REVIEW = HERE
SOURCE = RUNTIME / 'try2-usability/vmopt-20261103-try2-long-media-gap-v2/guest.cpio'
CANDIDATE = HERE / 'guest-three-entry.cpio'
OLD_CPIO = MAC / 'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio'
ARCHIVED = RUNTIME / 'try2-usability/runs/try2mssallinternal-c017e6ed/observer-source'
sys.path.insert(0, str(ARCHIVED))
from cpio_audit import audit
from gate_input_usability import InputGate
from restore_api103_v2 import restore_native_api
import classify_serial
import verify as ap_static

PINS = {
    'baseline': '854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669',
    'source': 'eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d',
    'candidate': 'bb618bd24f0b504edb14820da4d8204c4b1517cc225e4633eb43f5884f3fff02',
    'old_cpio': '7d151d8f1e363c66a947724fd65c5b818e8037347c886d8b0f133c970ad1f862',
}
ALLOW = {
    'usr/bin/bootin.elf': ('dab3ce4b6c28a6c9ffd9f0b893dce1d08f3ee7302a09df87e518409e728be2f2',
                           '72480247f8d2a1eeaab076b880c35279c6c94284649e267066f5ea10de6622a6', 23960),
    'usr/bin/im.elf': ('5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91',
                       '87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec', 40920),
}
AP_ALLOW = ('545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
            'a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067',
            79015712, 50520424)
LOCKS = (MAC / 'outputs/fx3-vm/.run.lock', FX3 / 'menu-repair-01/runtime/.run.lock')
MAX_TOTAL = 180
OBSERVE_LIMIT = 120  # Leaves at least 60 s for the 20 s guest ACK and process cleanup.
MARKER_PATTERNS = {
    'verify': rb'FX3_TRACE_ABI_VERIFY_RC=(-?\d+)',
    'list': rb'FX3_TRACE_ABI_LIST_RC=(-?\d+)',
    'true': rb'FX3_TRACE_ABI_TRUE_RC=(-?\d+)',
    'not_ready': rb'FX3_TRACE_ABI_NOT_READY[^\r\n]*',
    'natural_bootin': rb'FX3_AP_NATURAL_BOOTIN_BEGIN[^\r\n]*',
    'im_map': rb'[0-9a-f]{8}-[0-9a-f]{8} r-xp [^\r\n]* /usr/bin/im\.elf',
    'ap_guard': rb'FX3_(?:PRESET_CONTEXT_BIND_REJECT|UI_GATE_BIND_FAIL|TIMER_BIND_FAILED|MEDIA_BIND_REJECT module=A)[^\r\n]*',
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify():
    vol = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    if vol.get('VolumeUUID') != 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':
        raise RuntimeError('volume UUID mismatch')
    for key, path in [('baseline', BASE), ('source', SOURCE), ('candidate', CANDIDATE), ('old_cpio', OLD_CPIO)]:
        if sha(path) != PINS[key]:
            raise RuntimeError(key + ' SHA mismatch')
    baseline = json.loads(BASE.read_text())
    for row in baseline['sha256'].values():
        path = Path(row['path'])
        if path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
            raise RuntimeError('fixed platform artifact drift: ' + str(path))
    static = json.loads((REVIEW / 'receipt.json').read_text())
    if (static.get('status') != 'BUILT_AND_INDEPENDENTLY_STATIC_VERIFIED_NOT_RUN'
            or static.get('candidate_sha256') != PINS['candidate']
            or static.get('fx3_baseline_cpio_sha256') != PINS['source']
            or static.get('other_members_header_and_payload_equal') is not True
            or static.get('bsdtar_names_equal') is not True):
        raise RuntimeError('independent three-entry static review mismatch')
    report = audit(CANDIDATE, OLD_CPIO)
    changed = set(report['baseline_ELF_changed_or_missing'])
    members = {r['path']: r for r in report['members']}
    if (report['member_count'] != 1140 or report['original_baseline_ELF_members'] != 20
            or report['unpack_parent_order_errors'] or report['safe_to_unpack'] is not False
            or changed != set(ALLOW) or report['candidate_cpio_sha256'] != PINS['candidate']
            or report['baseline_cpio_sha256'] != PINS['old_cpio']):
        raise RuntimeError('original CPIO gate differed beyond exact two ELF changes')
    for name, (before, after, size) in ALLOW.items():
        row = members[name]
        if row['sha256'] != after or row['bytes'] != size:
            raise RuntimeError('allowlisted payload mismatch: ' + name)
        review_row = next(r for r in static['expected_exact_identity_exceptions'] if r['name'] == name)
        if (review_row['fx3_sha256'] != before or review_row['candidate_sha256'] != after
                or review_row['candidate_bytes'] != size):
            raise RuntimeError('independent review allowlist mismatch: ' + name)
    originals, original_end = ap_static.scan(SOURCE)
    candidates, candidate_end = ap_static.scan(CANDIDATE)
    if (len(originals) != 1141 or len(candidates) != 1141 or original_end != 453184500
            or candidate_end != 424689212 or CANDIDATE.stat().st_size != 453184500):
        raise RuntimeError('full FX3 CPIO structure or fixed length changed')
    three = {**{k:(v[0],v[1],v[2],v[2]) for k,v in ALLOW.items()},
             'usr/lib/appFw.so': AP_ALLOW}
    with SOURCE.open('rb') as old, CANDIDATE.open('rb') as new:
        for a,b in zip(originals,candidates):
            name=a['name']
            if name != b['name'] or a['mode'] != b['mode'] or a['headname'] != b['headname']:
                raise RuntimeError('member order/name/mode changed: '+name)
            if name in three:
                before,after,old_bytes,new_bytes=three[name]
                if (a['size']!=old_bytes or b['size']!=new_bytes
                        or ap_static.hash_member(SOURCE,a)!=before
                        or ap_static.hash_member(CANDIDATE,b)!=after):
                    raise RuntimeError('exact three-member exception changed: '+name)
                expected_header=a['header'] if name!='usr/lib/appFw.so' else a['header'][:54]+f'{new_bytes:08x}'.encode()+a['header'][62:]
                if b['header']!=expected_header:raise RuntimeError('allowlisted header changed: '+name)
            else:
                if a['header']!=b['header'] or a['size']!=b['size'] or a['pad']!=b['pad']:
                    raise RuntimeError('unallowlisted member metadata changed: '+name)
                ap_static.equal_ranges(old,new,a['data'],b['data'],a['size'])
    if static['dtb_chosen'] != {'linux,initrd-start':'0x440000000','linux,initrd-end':'0x45b030bf4'}:
        raise RuntimeError('frozen DTB initrd range changed')
    report={k:v for k,v in report.items() if k not in ('init_text','members')}
    report['exact_full_cpio_allowlist']=list(three)
    report['all_other_members_compared']=1140-len(three)
    return baseline, report


class QMP:
    def __init__(self, run):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(4)
        # macOS sockaddr_un rejects the long absolute run path; QEMU uses a
        # relative socket in cwd, so connect with the same short name.
        previous = Path.cwd()
        try:
            os.chdir(run)
            self.sock.connect('q')
        finally:
            os.chdir(previous)
        self.stream = self.sock.makefile('rb')
        self.greeting = json.loads(self.stream.readline())
        self.serial = 0
        self.events = []

    def call(self, command, arguments=None):
        self.serial += 1
        token = 'entry-' + str(self.serial)
        packet = {'execute': command, 'id': token}
        if arguments is not None:
            packet['arguments'] = arguments
        self.sock.sendall((json.dumps(packet) + '\n').encode())
        while True:
            line = self.stream.readline()
            if not line:
                raise RuntimeError('QMP stream closed on ' + command)
            row = json.loads(line)
            if row.get('id') == token:
                if 'error' in row:
                    raise RuntimeError('QMP ' + command + ': ' + repr(row['error']))
                return row.get('return')
            self.events.append(row)

    def close(self):
        self.stream.close()
        self.sock.close()


def extract(serial):
    if not serial.exists():
        return {'available': False, 'reason': 'serial_log_not_created'}
    data = serial.read_bytes()
    found = {}
    for name, pat in MARKER_PATTERNS.items():
        m = re.search(pat, data)
        found[name] = None if m is None else {'byte_range': [m.start(), m.end()], 'raw': m.group().decode(errors='replace')}
    return {'available': True, 'bytes': len(data), 'sha256': sha(serial), 'first': found,
            'im_process_label_count': data.count(b'FX3_AP_IM_PROCESS='),
            'synthetic_key_count': data.count(b'FX3_SYNTH_KEY'),
            'fx3_boot_queue_not_fx6_AP_entry_evidence': True}


class IncrementalMarkers:
    def __init__(self, path):
        self.path = path
        self.offset = 0
        self.tail = b''
        self.first = {name: None for name in MARKER_PATTERNS}

    def poll(self):
        if not self.path.exists():
            return self.first
        with self.path.open('rb') as stream:
            stream.seek(self.offset)
            chunk = stream.read()
            self.offset = stream.tell()
        data = self.tail + chunk
        base = self.offset - len(data)
        for name, pattern in MARKER_PATTERNS.items():
            if self.first[name] is None:
                match = re.search(pattern, data)
                if match:
                    self.first[name] = {'byte_range': [base + match.start(), base + match.end()],
                                        'raw': match.group().decode(errors='replace')}
        self.tail = data[-512:]
        return self.first


class APHealthMonitor:
    """Incremental exact-line AP diagnostics plus all pinned parent failures."""
    def __init__(self, path):
        self.path=Path(path)
        self.offset=0
        self.partial=b''
        self.lines=0
        self.failure=None
        self.diagnostics=[]
        self.loader_observations={k:[] for k in classify_serial.LOADERS}

    def poll(self):
        if not self.path.exists():return
        with self.path.open('rb') as stream:
            stream.seek(self.offset)
            chunk=stream.read()
            self.offset=stream.tell()
        parts=(self.partial+chunk).split(b'\n')
        self.partial=parts.pop()
        for part in parts:
            self._accept(part)

    def _accept(self,part):
        self.lines+=1
        result=classify_serial.classify(part+b'\n',PINS['candidate'])
        for name,rows in result['loader_all_observations'].items():
            self.loader_observations[name].extend({'line':self.lines,'column':x['column'],'value':x['value']} for x in rows)
        self.diagnostics.extend({'line':self.lines,'which':x['which'],'text':x['text']}
                                for x in result['events'] if x['kind']=='expected_fx3_diagnostic_only')
        if result['first_fault'] and self.failure is None:
            self.failure={'line':self.lines,'kind':result['first_fault']['kind'],
                          'text':result['first_fault']['text']}

    def finish(self):
        self.poll()
        if self.partial:
            self._accept(self.partial)
            self.partial=b''

    def snapshot(self):
        return {'lines':self.lines,'failure':self.failure,'diagnostics':self.diagnostics,
                'loader_all_observations':self.loader_observations,
                'partial_line_bytes':len(self.partial)}


def cleanup_owned(qemu,qmp,guest_gate,run,cleanup,restore_fn=restore_native_api):
    """Parent run's API16 restore/own-process cleanup, injectable for no-VM test."""
    cleanup['attempted']=True
    if qemu is not None and qemu.poll() is None and qmp is not None:
        try:
            qmp.call('stop')
            cleanup['guest_stopped']=True
            result=restore_fn(qmp.call,guest_gate,run,timeout=20)
            cleanup['restore']=result
            cleanup['API16_restored']=result['passed']
        except Exception as exc:
            cleanup['restore_error']=repr(exc)
        try:
            qmp.call('quit')
            cleanup['quit_sent']=True
        except Exception as exc:
            cleanup['quit_error']=repr(exc)
    if qemu is not None and qemu.poll() is None:
        try:
            qemu.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(qemu.pid,signal.SIGTERM)
            try:
                qemu.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(qemu.pid,signal.SIGKILL)
                qemu.wait(timeout=3)
                cleanup['forced_own_process_kill']=True
    if qmp is not None:qmp.close()
    if guest_gate.sock is not None:guest_gate.sock.close()


def main():
    baseline, old_audit = verify()
    held = []
    for path in LOCKS:
        stream = path.open('rb')
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            stream.close()
            for item in held:
                fcntl.flock(item, fcntl.LOCK_UN)
                item.close()
            raise RuntimeError('existing FX3 run lock held; no VM started')
        held.append(stream)
    run = HERE / 'runs' / ('fx6ap-' + uuid.uuid4().hex[:8])
    run.mkdir(parents=True)
    run.chmod(0o700)
    args = list(baseline['fx3_vm_command'])
    args[20] = 'file:' + str(run / 'serial.log')
    args[31] = 'loader,file=' + str(CANDIDATE) + ',addr=0x440000000,force-raw=on'
    frozen = baseline['fx3_vm_command']
    if (len(args) != 34 or args[31].split(',')[2:] != frozen[31].split(',')[2:]
            or any(args[i] != frozen[i] for i in range(34) if i not in (20, 31))):
        raise RuntimeError('QEMU command escaped frozen two-path delta')
    env = os.environ.copy()
    env.update(baseline['model_env'])
    (run / 'command.json').write_text(json.dumps({'args': args, 'cwd': str(run),
        'model_env': baseline['model_env'], 'baseline_sha256': PINS['baseline'],
        'candidate_sha256': PINS['candidate'], 'frozen_argv_changed_indices': [20, 31],
        'relative_qmp_gdb': ['q', 'g'], 'key_budget': 0,
        'old_cpio_audit': old_audit, 'old_20_ELF_allowlist': ALLOW,
        'separate_full_CPIO_AP_allowlist': AP_ALLOW,
        'observation_goal': 'first_real_fault_or_exact_diagnostics_or_bounded_unknown'}, indent=2) + '\n')
    shutil.copyfile(__file__, run / 'observer-source.py')
    (run / 'source-sha256.json').write_text(json.dumps({
        'runner': sha(__file__), 'static_verify_py': sha(REVIEW / 'verify.py'),
        'review_receipt': sha(REVIEW / 'receipt.json'),
        'helper_audit_py': sha(REVIEW / 'audit_preloads.py'),
        'helper_audit_receipt': sha(REVIEW / 'preload-audit.json'),
        'classifier': sha(REVIEW / 'classify_serial.py'),
        'old_cpio_audit': sha(ARCHIVED / 'cpio_audit.py'),
        'restore_api103_v2': sha(ARCHIVED / 'restore_api103_v2.py'),
        'input_gate': sha(ARCHIVED / 'gate_input_usability.py'),
        'log_monitor': sha(ARCHIVED / 'trial_log_v4_mss.py')}, indent=2) + '\n')
    qemu = None
    qmp = None
    guest_gate = InputGate(run)
    watcher = APHealthMonitor(run / 'serial.log')
    markers = IncrementalMarkers(run / 'serial.log')
    start = time.monotonic()
    begun = datetime.datetime.now(datetime.timezone.utc).isoformat()
    stop = None
    error = None
    cleanup = {'attempted': False, 'API16_restored': False, 'quit_sent': False}
    original_handler = signal.getsignal(signal.SIGINT)
    interrupted = {'value': False}

    def on_interrupt(signum, frame):
        interrupted['value'] = True

    signal.signal(signal.SIGINT, on_interrupt)
    try:
        with (run / 'host-stdout.log').open('wb') as stdout, (run / 'host-stderr.log').open('wb') as stderr:
            try:
                def limit_files():
                    resource.setrlimit(resource.RLIMIT_FSIZE, (512 * 1024 * 1024, 512 * 1024 * 1024))
                    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

                qemu = subprocess.Popen(args, cwd=run, env=env, stdout=stdout, stderr=stderr,
                                        start_new_session=True, preexec_fn=limit_files)
                (run / 'pid.json').write_text(json.dumps({'qemu_pid': qemu.pid, 'owner_pid': os.getpid()}) + '\n')
                while not (run / 'q').exists() and qemu.poll() is None and time.monotonic() - start < 10:
                    time.sleep(.05)
                if qemu.poll() is not None or not (run / 'q').exists():
                    raise RuntimeError('QEMU exited before QMP bind')
                qmp = QMP(run)
                qmp.call('qmp_capabilities')
                qmp.call('cont')
                while True:
                    watcher.poll()
                    first = markers.poll()
                    for name in ('verify', 'list', 'true'):
                        row = first.get(name)
                        if row and not row['raw'].endswith('=0'):
                            stop = 'loader_' + name + '_nonzero'
                            break
                    if stop:
                        break
                    if first.get('not_ready'):
                        stop = 'loader_not_ready'
                        break
                    if watcher.failure:
                        stop = 'first_health_fault'
                        break
                    if qemu.poll() is not None:
                        stop = 'qemu_early_exit'
                        break
                    if interrupted['value']:
                        stop = 'operator_interrupt'
                        break
                    if time.monotonic() - start >= OBSERVE_LIMIT:
                        stop = 'observation_budget_end'
                        break
                    time.sleep(.25)
            except Exception as exc:
                error = repr(exc)
                stop = stop or 'host_exception'
            finally:
                cleanup_owned(qemu,qmp,guest_gate,run,cleanup)
    finally:
        signal.signal(signal.SIGINT, original_handler)
        watcher.finish()
        serial = extract(run / 'serial.log')
        input_pins = {key: sha(path) for key, path in [('baseline', BASE), ('source', SOURCE),
                       ('candidate', CANDIDATE), ('old_cpio', OLD_CPIO)]}
        unchanged = input_pins == PINS
        for item in held:
            fcntl.flock(item, fcntl.LOCK_UN)
            item.close()
        locks = []
        for path in LOCKS:
            with path.open('rb') as item:
                try:
                    fcntl.flock(item, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    free = True
                    fcntl.flock(item, fcntl.LOCK_UN)
                except BlockingIOError:
                    free = False
            locks.append({'path': str(path), 'free': free})
        try:
            os.kill(qemu.pid, 0)
            pid_absent = False
        except (AttributeError, ProcessLookupError):
            pid_absent = True
        if watcher.failure or stop in ('loader_not_ready','qemu_early_exit','host_exception'):
            observation_outcome='actual_fault_or_unproven_guard'
        elif watcher.diagnostics:
            observation_outcome='exact_old_fx3_diagnostic_only'
        else:
            observation_outcome='bounded_unknown'
        receipt = {'run': str(run), 'created_utc': begun, 'duration_seconds': time.monotonic() - start,
                   'stop_cause': stop, 'host_error': error, 'qemu_pid': None if qemu is None else qemu.pid,
                   'qemu_exit': None if qemu is None else qemu.returncode,
                   'process_reaped': qemu is not None and qemu.poll() is not None,
                   'PID_absent': pid_absent, 'inputs_unchanged': unchanged,
                   'input_pins': input_pins, 'locks': locks, 'serial': serial,
                   'serial_health_failure': watcher.failure, 'cleanup': cleanup,
                   'host_classifier': watcher.snapshot(), 'observation_outcome': observation_outcome,
                   'key_steps': 0, 'synthetic_events': 0,
                   'fx3_platform_unchanged': True,
                   'fx6_system_or_menu_proven': False,
                   'fx6_AP_entry_or_ABI_proven': False,
                   'im_PT_LOAD_new_logic_proven': False}
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n')
        print(json.dumps({'run': str(run), 'stop': stop, 'error': error,
                          'qemu_exit': receipt['qemu_exit'], 'API16_restored': cleanup['API16_restored'],
                          'locks_free': all(x['free'] for x in locks)}, ensure_ascii=False), flush=True)
    if not (qemu is not None and qemu.returncode == 0 and pid_absent and unchanged
            and all(x['free'] for x in locks) and cleanup['API16_restored']
            and receipt['duration_seconds'] <= MAX_TOTAL and
            stop in ('observation_budget_end','first_health_fault','loader_verify_nonzero',
                     'loader_list_nonzero','loader_true_nonzero','loader_not_ready','qemu_early_exit')):
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
