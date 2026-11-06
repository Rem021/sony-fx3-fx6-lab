#!/usr/bin/env python3
"""Actual frozen r6 HostRunner/Observer/QMP/RSP four-stop with FX3MS2 provider.

No VM, no QEMU process, no target ELF execution: fake QMP/RSP socketpairs and a
fake launcher process.  The TLS reader is a fixture; this is host-flow evidence,
not target Sysregs verification.
"""
import json, socket, struct, sys, tempfile, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
CAND = HERE
R6 = Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-backup-read-observer-candidate')
sys.path.insert(0, str(HERE / 'host'))
sys.path.insert(0, str(R6 / 'observer'))
import host_runner as H
import live_runner_v2 as L
import fx3ms2 as FP
import run_candidate_v2 as ENTRY

APP = Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/grm-fbinit/appFw-future-skip.so')
FIX = HERE / 'fixtures/native-target-frame-v2.serial'
M = FP.FramedProviderV2().select(FIX.read_text())
BIAS = M['ap']['bias']
_b = APP.read_bytes()
_phoff = __import__('struct').unpack_from('<Q', _b, 32)[0]
_es, _n = __import__('struct').unpack_from('<HH', _b, 54)
IDENTITY_READS = 16 + (_es * _n) // 4 + 4
core = H.observer_core
checks = []
BUDGET = {}

def check(n, f):
    f()
    checks.append(n)
    print('PASS', n, flush=True)

def packet(s):
    r = s.encode()
    return b'$' + r + b'#' + f'{sum(r) & 255:02x}'.encode()

class QMPServer:
    def __init__(self, sock):
        self.sock = sock
        self.state = 'prelaunch'
        self.running = False
        self.calls = []
        self.err = None
        self.caps = False
    def run(self):
        try:
            f = self.sock.makefile('rwb', buffering=0)
            f.write(b'{"QMP":{"version":{"qemu":{"major":1,"minor":0},"package":""},"capabilities":[]}}\n')
            while True:
                line = f.readline()
                if not line:
                    break
                q = json.loads(line)
                cmd = q['execute']
                self.calls.append(cmd)
                if not self.caps and cmd != 'qmp_capabilities':
                    raise RuntimeError('command before capabilities')
                if cmd == 'qmp_capabilities':
                    self.caps = True
                    resp = {}
                elif cmd == 'query-status':
                    resp = {'status': self.state, 'running': self.running}
                elif cmd == 'cont':
                    self.state = 'running'
                    self.running = True
                    resp = {}
                elif cmd == 'stop':
                    self.state = 'paused'
                    self.running = False
                    resp = {}
                elif cmd == 'quit':
                    f.write((json.dumps({'id': q['id'], 'return': {}}) + '\n').encode())
                    break
                else:
                    resp = {}
                f.write((json.dumps({'id': q['id'], 'return': resp}) + '\n').encode())
        except BaseException as e:
            self.err = repr(e)
        finally:
            try:
                self.sock.close()
            except Exception:
                pass

class GDBServer:
    def __init__(self, sock, corrupt_header=False):
        self.sock = sock
        self.err = None
        self.cmds = []
        self.continued = 0
        self.state = 'paused'
        self.stop_index = 0
        self.corrupt_header = corrupt_header
    def _read_packet(self):
        b = self.sock.recv(1)
        if not b:
            return None
        while b in (b'+', b'-', b'\n', b'\r'):
            b = self.sock.recv(1)
            if not b:
                return None
        if b != b'$':
            raise RuntimeError('bad framing ' + repr(b))
        raw = b''
        while True:
            c = self.sock.recv(1)
            if c == b'#':
                break
            raw += c
        tail = self.sock.recv(2)
        if int(tail, 16) != sum(raw) & 255:
            raise RuntimeError('bad checksum')
        self.sock.sendall(b'+')
        return raw.decode()
    def _reply(self, body):
        self.sock.sendall(packet(body))
    def _send_stop(self):
        names = ['entry214', 'return214', 'entry218', 'return218']
        n = names[self.stop_index]
        self.stop_index += 1
        msg = b'T05thread:1;'
        self.sock.sendall(b'$' + msg + b'#' + f'{sum(msg) & 255:02x}'.encode())
        self.state = 'stopped'
    def _regs(self):
        n = self.stop_index - 1
        k = core.KEYS[0] if n in (0, 1) else core.KEYS[1]
        fp = 0x7ed3d12290
        buf = fp + k['slot_off']
        r = [0] * 33
        r[29] = fp
        if n in (0, 2):
            r[0] = buf
            r[30] = BIAS + k['return_va']
            r[32] = BIAS + k['thunk_va']
        else:
            r[0] = 0xfffffc03
            r[32] = BIAS + k['return_va']
        return struct.pack('<33Q', *r).hex()
    def _mem(self, addr, size):
        k = core.KEYS[0] if self.stop_index <= 2 else core.KEYS[1]
        fp = 0x7ed3d12290
        buf = fp + k['slot_off']
        if addr == buf:
            return (b'\x01\x00\x00\x00' if self.stop_index in (1, 3) else b'\x16\x16\x16\x16').hex()
        if self.corrupt_header and addr == BIAS:
            return '00000000'
        if addr in (BIAS + k['thunk_va'], BIAS + k['return_va']):
            return (bytes.fromhex(k['thunk_word']) if addr == BIAS + k['thunk_va'] else bytes.fromhex(k['return_word'])).hex()
        va = addr - BIAS
        b = APP.read_bytes()
        for s in core.elf_loads(APP):
            if s['va'] <= va and va + size <= s['va'] + s['filesz']:
                off = s['fileoff'] + va - s['va']
                return b[off:off + size].hex()
        raise RuntimeError('unmapped m ' + hex(addr))
    def _xml(self):
        return '<target><architecture>aarch64</architecture><feature name="org.gnu.gdb.aarch64.core"><reg name="x0" regnum="0" bitsize="64"/><reg name="x29" regnum="29" bitsize="64"/><reg name="x30" regnum="30" bitsize="64"/><reg name="sp" regnum="31" bitsize="64"/><reg name="pc" regnum="32" bitsize="64"/><reg name="SP_EL0" regnum="100" bitsize="64"/><reg name="TPIDR_EL0" regnum="101" bitsize="64"/></feature></target>'
    def run(self):
        try:
            while True:
                raw = self._read_packet()
                if raw is None:
                    break
                self.cmds.append(raw)
                if raw.startswith('qXfer:features:read:target.xml:'):
                    self._reply('l' + self._xml())
                    continue
                if raw.startswith('Qqemu.PhyMemMode') or raw.startswith('qqemu.PhyMemMode'):
                    self._reply('OK')
                    continue
                if raw.startswith('Hg') or raw.startswith('Hc'):
                    self._reply('OK')
                    continue
                if raw.startswith('Z1,') or raw.startswith('z1,'):
                    self._reply('OK')
                    continue
                if raw == 'g':
                    self._reply(self._regs())
                    continue
                if raw.startswith('p'):
                    self._reply('4074ff5c7f000000' if raw == 'p65' else '0000000000000000')
                    continue
                if raw.startswith('m'):
                    a, s = raw[1:].split(',')
                    self._reply(self._mem(int(a, 16), int(s, 16)))
                    continue
                if raw == 'c':
                    self.continued += 1
                    self.sock.sendall(b'+')
                    self._send_stop()
                    continue
                raise RuntimeError('unexpected GDB ' + raw[:40])
        except BaseException as e:
            self.err = repr(e)
        finally:
            try:
                self.sock.close()
            except Exception:
                pass

def make_deps(root, corrupt_header=False):
    qa, qb = socket.socketpair()
    ga, gb = socket.socketpair()
    qs = QMPServer(qb)
    gs = GDBServer(gb, corrupt_header=corrupt_header)
    tq = threading.Thread(target=qs.run)
    tg = threading.Thread(target=gs.run)
    tq.start()
    tg.start()
    q = H.QMP(sock=qa)
    class QProxy:
        def call(self, c, args=None, deadline=None):
            return q.call(c, args, deadline)
        def close(self):
            q.close()
    def writer():
        p = Path(root) / 'serial.log'
        while not p.exists():
            time.sleep(0.01)
        raw = FIX.read_bytes()
        cut = 40
        with p.open('wb') as f:
            f.write(raw[:cut])
            f.flush()
            time.sleep(0.1)
            f.write(raw[cut:])
            f.flush()
    threading.Thread(target=writer, daemon=True).start()
    def tls():
        return 0x7f5cff740
    d = {
        'verify_artifacts': lambda: {},
        'hash_checker': lambda p: H.baseline_binding.TARGET_SHA if str(p) == str(H.baseline_binding.TARGET) else H.baseline_binding.APP_SHA,
        'uuid_checker': lambda: True,
        'run_root': str(root),
        'lock_factory': lambda: type('L', (), {'acquire': lambda s: None, 'release': lambda s: None})(),
        'launcher': lambda *a: type('P', (), {'returncode': 0, 'wait': lambda s, timeout: 0})(),
        'qmp_factory': lambda p, deadline=None: QProxy(),
        'rsp_factory': lambda p, deadline=None: H.RSP(sock=ga, deadline=deadline),
        'mapping_provider': lambda *a: M,
        'tls_reader': tls,
        'runtime_evidence': False,
    }
    return d, (qa, qb, ga, gb, qs, gs, tq, tg)

def close_parts(parts):
    for s in parts[:4]:
        try:
            s.close()
        except Exception:
            pass
    for t in parts[6:]:
        t.join(1)

def test_success():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / 'run'
        holder = {}
        def rf(r):
            deps, parts = make_deps(r)
            holder['parts'] = parts
            holder['runner'] = L.build_runner(r, deps_factory=lambda: deps)
            return holder['runner']
        rf.__offline_fake__ = True
        rc = ENTRY.main(['--approved-token', ENTRY.TOKEN, '--new-run-approval', '--run-root', str(root)], rf, allow_offline_fake=True)
        parts = holder['parts']
        qs = parts[4]
        gs = parts[5]
        rec = json.loads((root / 'receipt.json').read_text())
        first = json.loads((root / 'first-stop-identity.json').read_text())
        assert rc == 0, (rc, root)
        assert rec['two_keys_observed'] and rec['host_cleanup_complete'] and rec['guest_restore_status'] == 'unknown_not_attempted'
        assert gs.continued == 4
        assert not (root / 'prearm-identity.json').exists()
        assert first['checked_at_first_appfw_stop'] is True
        assert first['prearm_identity_reused_across_epochs'] is False
        assert first['mapping_snapshot_atomic'] is False
        assert first['identity']['words'] and len(first['identity']['words']) == 4
        assert first['identity_reads_expected'] == IDENTITY_READS
        assert first['shared_reads_after_first_stop'] == IDENTITY_READS + 2
        shared = holder['runner'].prearm_box['shared_rsp']
        assert shared.rejected == 0
        assert shared.reads == IDENTITY_READS + 8, (shared.reads, IDENTITY_READS)
        assert shared.reads <= 128
        assert sum(1 for c in gs.cmds if c.startswith('m')) == shared.reads
        assert sum(1 for c in gs.cmds if c.startswith('Z1,')) == 4
        BUDGET['success'] = {
            'identity_reads': IDENTITY_READS,
            'first_stop_reads_after_identity_and_two_entry_reads': first['shared_reads_after_first_stop'],
            'observer_key_reads': shared.reads - IDENTITY_READS,
            'total_reads': shared.reads,
            'max_reads': shared.max_reads,
            'remaining': shared.max_reads - shared.reads,
            'gdb_m_commands': sum(1 for c in gs.cmds if c.startswith('m')),
            'prearm_identity_reused_across_epochs': False,
            'rejected': shared.rejected,
        }
        close_parts(parts)
check('actual_HostRunner_four_stop_prearm_identity_via_entry', test_success)

def test_identity_failure_no_arm():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / 'run'
        holder = {}
        def rf(r):
            deps, parts = make_deps(r, corrupt_header=True)
            holder['parts'] = parts
            holder['runner'] = L.build_runner(r, deps_factory=lambda: deps)
            return holder['runner']
        rf.__offline_fake__ = True
        rc = ENTRY.main(['--approved-token', ENTRY.TOKEN, '--new-run-approval', '--run-root', str(root)], rf, allow_offline_fake=True)
        parts = holder['parts']
        gs = parts[5]
        rec = json.loads((root / 'receipt.json').read_text())
        assert rc == 1
        assert rec['status'] == 'error'
        assert rec['records'] == []
        assert not (root / 'first-stop-identity.json').exists()
        assert 'live ELF header mismatch' in str(rec.get('error'))
        close_parts(parts)
check('first_stop_identity_failure_no_key_record', test_identity_failure_no_arm)

def test_shared_budget_exhaustion_before_send():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / 'run'
        holder = {}
        def rf(r):
            deps, parts = make_deps(r)
            holder['parts'] = parts
            # exactly the identity scan: the first Observer read must be rejected
            holder['runner'] = L.build_runner(r, deps_factory=lambda: deps, shared_budget=IDENTITY_READS)
            return holder['runner']
        rf.__offline_fake__ = True
        rc = ENTRY.main(['--approved-token', ENTRY.TOKEN, '--new-run-approval', '--run-root', str(root)], rf, allow_offline_fake=True)
        parts = holder['parts']; gs = parts[5]
        shared = holder['runner'].prearm_box['shared_rsp']
        rec = json.loads((root / 'receipt.json').read_text())
        assert rc == 1
        assert rec['status'] == 'error'
        assert shared.reads == IDENTITY_READS
        assert shared.rejected == 1
        assert sum(1 for c in gs.cmds if c.startswith('m')) == IDENTITY_READS
        assert 'shared RSP read budget exhausted' in str(rec.get('error'))
        BUDGET['over_budget'] = {
            'budget_reads': IDENTITY_READS,
            'total_reads': shared.reads,
            'rejected': shared.rejected,
            'gdb_m_commands': sum(1 for c in gs.cmds if c.startswith('m')),
            'receipt_error': rec.get('error'),
            'rejected_before_wrapped_command': True,
        }
        close_parts(parts)
check('shared_budget_exhaustion_rejected_before_105th_read', test_shared_budget_exhaustion_before_send)

BUDGET['tls_reader'] = 'fixture stub, not actual Sysregs'
BUDGET['vm_started'] = False
BUDGET['target_execution'] = False
BUDGET['note'] = ('one shared 128 x 4B budget covers prearm identity and Observer reads; '
                  'ObserverV2 reuses the prearm paused-epoch identity; over-budget read is rejected '
                  'before the wrapped RSP sends the next command')
(CAND / 'receipts/rsp-budget.json').write_text(json.dumps(BUDGET, indent=2) + '\n')
out = {'schema': 'fx6-map-collector-shortread-e2e-v1',
       'status': 'PASS_OFFLINE_ACTUAL_HOSTRUNNER',
       'tls_reader': 'fixture stub, not actual Sysregs',
       'target_execution': False,
       'vm_started': False,
       'rsp_budget': 'receipts/rsp-budget.json',
       'budget': BUDGET,
       'tests': len(checks), 'cases': checks}
(HERE / 'receipts/e2e-hostrunner-v2.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(out, indent=2))
