"""Offline execution of the runner's real input AST block with fake QMP/InputGate."""
import ast
import hashlib
import json
import re
import tempfile
import textwrap
import threading
import time
import types
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
from pre_input_observation import capture, PreInputSnapshotError
from gate_input_usability import valid_command

SOURCE = (ROOT / 'run_trial_v25_diag_r3.py').read_text()
TREE = ast.parse(SOURCE)
INPUT = next(node for node in ast.walk(TREE) if isinstance(node, ast.If)
             and 'proposed is not None and not trial.stop.is_set()' in
             (ast.get_source_segment(SOURCE, node.test) or ''))
BLOCK = textwrap.dedent(ast.get_source_segment(SOURCE, INPUT))
# Execute the actual runner block, including qmp stop, optional capture,
# host_step increment, InputGate.command, qmp cont, and stop/cancel break.
DRIVE = 'def drive(ctx):\n    host_step=ctx.host_step\n    proposed=ctx.proposed\n    current_command=None\n    while True:\n' + textwrap.indent(BLOCK, '        ') + '\n        break\n    return host_step,current_command\n'
assert 'capture_pre_input_observation' in DRIVE and 'input_gate.command' in DRIVE
assert DRIVE.index("qmp('stop')") < DRIVE.index('capture_pre_input_observation') < DRIVE.index('host_step += 1') < DRIVE.index('input_gate.command') < DRIVE.index("qmp('cont')")
main = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
assert any(isinstance(n, ast.Try) and INPUT in list(ast.walk(n)) and
           'restore_native_api' in ast.unparse(n.finalbody) and "qmp('quit')" in ast.unparse(n.finalbody)
           for n in ast.walk(main)), 'actual runner must preserve enclosing API16/quit cleanup finally'

SNAPSHOTS = [{'name':'ui-gate-counters.bin','address':0x41dc00000,'size':0x10000},
             {'name':'osd-ring-final.bin','address':0x41e000000,'size':0x1000000}]

class Clock:
    def __init__(self): self.value=0.0
    def __call__(self): return self.value

class FakeQMP:
    def __init__(self, transport, *, mode='normal', stop=None, clock=None):
        self.transport=transport;self.mode=mode;self.stop=stop;self.clock=clock;self.calls=[]
    def __call__(self,name,arguments=None,*,timeout=None):
        self.calls.append((name,arguments,timeout))
        if name=='stop':
            if self.mode=='stop_error':return {'error':{'class':'GenericError'}}
            if self.mode=='stop_unknown':self.transport.send_unknown=True
            return {'return':{}}
        if name=='query-status':
            if self.mode=='query_timeout':raise TimeoutError('fake QMP query timeout')
            if self.mode=='query_error':return {'error':{'class':'GenericError'}}
            if self.mode=='query_budget':self.clock.value=2.1
            return {'return':{'running':self.mode=='running','status':'running' if self.mode=='running' else 'paused'}}
        if name=='human-monitor-command':
            if self.mode=='hmp_timeout':raise TimeoutError('fake QMP pmemsave timeout')
            if self.mode=='hmp_error':return {'error':{'class':'GenericError'}}
            m=re.fullmatch(r'pmemsave (0x[0-9a-f]+) (0x[0-9a-f]+) "(.+)"',arguments['command-line'])
            assert m, arguments
            address,size,path=int(m[1],16),int(m[2],16),Path(m[3])
            if self.mode=='hmp_save_error':raise OSError('fake host file save error')
            if self.mode=='wrong_length':size-=1
            path.write_bytes(bytes([0x5a if address==0x41dc00000 else 0x4f])*size)
            if self.mode=='end_during_read' and address==0x41dc00000:self.stop.set()
            if self.mode=='transport_unknown_during_read':self.transport.send_unknown=True
            return {'return':''}
        if name=='cont':return {'return':{}}
        raise AssertionError(name)

class Trial:
    def __init__(self):self.stop=threading.Event();self.events=[]
    def fail(self,reason):self.stop.set()
    def update(self,**kw):self.__dict__.update(kw)

class Gate:
    delete_key=0x1f8
    def __init__(self):self.writes=[]
    def command(self,*args):self.writes.append(args);return {'step':args[0]}

class Case(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.run=Path(self.temp.name);self.trial=Trial();self.transport=types.SimpleNamespace(send_unknown=False)
        self.clock=Clock();self.qmp=FakeQMP(self.transport,stop=self.trial.stop,clock=self.clock)
        self.gate=Gate();self.journal=[];self.cleanup_calls=[]
        self.ns=types.SimpleNamespace(internal_hoststep=False,pre_input_snapshot_step=None,max_steps=4096)
    def drive(self,host_step=0,*,mode='normal'):
        self.qmp.mode=mode
        globals_=dict(qmp=self.qmp,ns=self.ns,transport=self.transport,run=self.run,
                      snapshots=SNAPSHOTS,trial=self.trial,log_monitor=types.SimpleNamespace(poll=lambda:None),
                      pre_input_stop_reason=lambda *a:None,phaseA_capture=None,shutdown_count_at_ready=0,
                      valid_command=valid_command,input_gate=self.gate,
                      capture_pre_input_observation=lambda *a: capture(*a,clock=self.clock) if mode in ('query_budget','receipt_budget','receipt_end') else capture(*a),
                      journal=self.journal,ring_reader=types.SimpleNamespace(last=3,current_record={'PNG_sha256':'a'}),
                      json=json,time=time,KEYS={0x1ab:'MENU'})
        # The outer try/finally is the actual main() enclosing structure,
        # verified above. This marker proves exceptions/cancellation unwind.
        ns={};exec(DRIVE,globals_,ns)
        ctx=types.SimpleNamespace(host_step=host_step,proposed={'key':0x1ab,'label':'MENU',
            'observed_frame':{'sequence':3,'PNG_sha256':'a'},'reason':'offline control-flow fixture',
            'requested_monotonic':time.monotonic(),'source':'test'})
        try:return ns['drive'](ctx)
        finally:self.cleanup_calls.append('original_finally_reachable')
    def receipt(self,step=1):
        return json.loads((self.run/f'pre-input-step-{step:04d}-receipt.json').read_text())
    def test_default_has_no_extra_qmp(self):
        step,current=self.drive()
        self.assertEqual(step,1);self.assertEqual(len(self.gate.writes),1)
        self.assertEqual([x[0] for x in self.qmp.calls],['stop','cont'])
        self.assertFalse(list(self.run.glob('pre-input-step-*')))
    def test_selected_once_two_exact_raw_files_and_repeat_rejected(self):
        self.ns.pre_input_snapshot_step=1
        step,_=self.drive()
        self.assertEqual(step,1);self.assertEqual(len(self.gate.writes),1)
        self.assertEqual([x[0] for x in self.qmp.calls],['stop','query-status','human-monitor-command','human-monitor-command','cont'])
        self.assertTrue(all(x[2] is None or 0 < x[2] <= 2.0 for x in self.qmp.calls))
        r=self.receipt();self.assertEqual(r['status'],'pending_postwrite_gate_no_guest_write');self.assertTrue(r['paused_proven'])
        self.assertEqual([x['bytes'] for x in r['items']],[0x10000,0x100])
        for item in r['items']:
            p=Path(item['path']);self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),item['sha256'])
            self.assertEqual(item['qmp_response'],{'return':''})
            self.assertLessEqual(item['host_monotonic_start'],item['host_monotonic_end'])
        self.assertEqual(self.receipt()['query_status_response']['return']['status'],'paused')
        # Next real step has no selected QMP reads.
        self.drive(host_step=1)
        self.assertEqual([x[0] for x in self.qmp.calls].count('query-status'),1)
        before=len(self.qmp.calls)
        with self.assertRaises(PreInputSnapshotError):
            capture(self.qmp,self.transport,self.run,SNAPSHOTS,{'return':{}},1,self.trial.stop)
        self.assertEqual(len(self.qmp.calls),before)
    def test_fail_closed_paths(self):
        for mode in ('stop_error','stop_unknown','query_error','query_timeout','running',
                     'hmp_error','hmp_timeout','hmp_save_error','wrong_length',
                     'transport_unknown_during_read','query_budget'):
            with self.subTest(mode=mode):
                with tempfile.TemporaryDirectory() as tmp:
                    self.run=Path(tmp);self.trial=Trial();self.transport=types.SimpleNamespace(send_unknown=False)
                    self.clock=Clock();self.qmp=FakeQMP(self.transport,mode=mode,stop=self.trial.stop,clock=self.clock)
                    self.gate=Gate();self.journal=[];self.cleanup_calls=[]
                    self.ns.pre_input_snapshot_step=1
                    with self.assertRaises(PreInputSnapshotError):self.drive(mode=mode)
                    self.assertEqual(self.gate.writes,[])
                    self.assertNotIn('cont',[x[0] for x in self.qmp.calls])
                    self.assertEqual(self.cleanup_calls,['original_finally_reachable'])
                    self.assertEqual(self.receipt()['status'],'failed_no_guest_write')
    def test_end_during_capture_no_key_or_extra_cont(self):
        self.ns.pre_input_snapshot_step=1
        step,current=self.drive(mode='end_during_read')
        self.assertEqual((step,current),(0,None))
        self.assertEqual(self.gate.writes,[])
        self.assertNotIn('cont',[x[0] for x in self.qmp.calls])
        self.assertEqual(self.receipt()['status'],'cancelled_no_guest_write')
        self.assertEqual(self.cleanup_calls,['original_finally_reachable'])
    def test_slow_receipt_write_and_end_during_receipt_fail_closed(self):
        self.ns.pre_input_snapshot_step=1
        original_dump=json.dump
        def slow_dump(*args,**kwargs):
            original_dump(*args,**kwargs)
            self.clock.value=2.5
        with mock.patch('pre_input_observation.json.dump',side_effect=slow_dump):
            with self.assertRaisesRegex(PreInputSnapshotError,'receipt persistence'):
                self.drive(mode='receipt_budget')
        self.assertEqual(self.gate.writes,[])
        self.assertNotIn('cont',[x[0] for x in self.qmp.calls])
        self.assertEqual(self.cleanup_calls,['original_finally_reachable'])
        self.assertEqual(self.receipt()['status'],'pending_postwrite_gate_no_guest_write')

        with tempfile.TemporaryDirectory() as tmp:
            self.run=Path(tmp);self.trial=Trial();self.transport=types.SimpleNamespace(send_unknown=False)
            self.clock=Clock();self.qmp=FakeQMP(self.transport,stop=self.trial.stop,clock=self.clock)
            self.gate=Gate();self.journal=[];self.cleanup_calls=[]
            def end_during_dump(*args,**kwargs):
                original_dump(*args,**kwargs)
                self.trial.stop.set()
            with mock.patch('pre_input_observation.json.dump',side_effect=end_during_dump):
                step,current=self.drive(mode='receipt_end')
            self.assertEqual((step,current),(0,None))
            self.assertEqual(self.gate.writes,[])
            self.assertNotIn('cont',[x[0] for x in self.qmp.calls])
            self.assertEqual(self.cleanup_calls,['original_finally_reachable'])

if __name__=='__main__':unittest.main(verbosity=2)
