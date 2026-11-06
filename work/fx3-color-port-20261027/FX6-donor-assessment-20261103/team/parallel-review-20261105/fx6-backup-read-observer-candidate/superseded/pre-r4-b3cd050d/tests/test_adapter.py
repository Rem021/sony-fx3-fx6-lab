#!/usr/bin/env python3
"""Offline lifecycle tests with fake QMP/QEMU/locks/observer; no VM."""
import hashlib,json,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent
spec=__import__('importlib.util').util.spec_from_file_location('adapter',HERE/'observer/execution_adapter.py');A=__import__('importlib.util').util.module_from_spec(spec);spec.loader.exec_module(A)
base=json.loads((HERE/'receipts/plan.json').read_text())
checks=[]
def check(n,f):f();checks.append(n)
class QMP:
 def __init__(self):self.calls=[];self.status='paused'
 def call(self,c):
  self.calls.append(c)
  if c=='query-status':return {'status':self.status}
  return {}
class Qemu:
 def __init__(self):self.waited=False
 def wait(self,timeout):self.waited=True;return 0
class Locks:
 def __init__(self):self.released=False
 def release(self):self.released=True
class Obs:
 def __init__(self,residual=False):self.residual=residual;self.records=[{}];self.arm_calls=0
 def arm(self):self.arm_calls+=1
 def on_stop(self,stop):self.records.append(stop);return {'stage':'ok'}
 def cleanup(self):return {'all_removed':not self.residual,'residual':['0xdead'] if self.residual else [],'results':[]}
def mk(tmp,obs,inherited=None):
 q=QMP();e=Qemu();l=Locks();a=A.Adapter(base,tmp,q,e,None,l,obs,inherited)
 p=a.prepare();assert p['args'][20].endswith('/serial.log') and p['args'][31]==base['new_initrd'];assert [i for i,(x,y) in enumerate(zip(base['qemu_argv'],p['args'])) if x!=y]==[20]
 return a,q,e,l
def normal():
 with tempfile.TemporaryDirectory() as d:
  called=[];obs=Obs();a,q,e,l=mk(Path(d),obs,lambda *x:called.append(1) or {'passed':True,'API16_restored':True,'original_bytes_verified':True,'ack_seen':True})
  a.arm();assert q.calls[:2]==['stop','query-status'];a.consume('T05thread:1;');r=a.cleanup()
  assert r['status']=='clean' and called and r['inherited_cleanup']=='completed';assert not r['guest_resumed'];assert 'qmp_quit' in a.calls and 'qemu_reaped' in a.calls and l.released
check('normal_private_path_arm_consume_cleanup',normal)
def residual():
 with tempfile.TemporaryDirectory() as d:
  called=[];a,q,e,l=mk(Path(d),Obs(residual=True),lambda *x:called.append(1))
  a.arm();r=a.cleanup()
  assert r['status']=='stopped_with_residual' and r['residual'] and not called;assert not r['guest_resumed'];assert 'qmp_quit' in a.calls and l.released
check('residual_breakpoint_no_inherited_no_resume',residual)
def missing_inherited():
 with tempfile.TemporaryDirectory() as d:
  a,q,e,l=mk(Path(d),Obs(),None);a.arm();r=a.cleanup();assert r['status']=='inherited_cleanup_required' and r['inherited_cleanup']=='required_missing';assert not r['guest_resumed'] and l.released
check('missing_inherited_cleanup_blocks_clean',missing_inherited)
def old_serial():
 with tempfile.TemporaryDirectory() as d:
  # existing nonempty private root must be rejected before any start
  Path(d,'serial.log').write_text('old')
  a=A.Adapter(base,Path(d),QMP(),Qemu(),None,Locks(),Obs())
  try:a.prepare()
  except RuntimeError:pass
  else:raise AssertionError('reused run root accepted')
check('reused_private_output_rejected',old_serial)
def deadline():
 with tempfile.TemporaryDirectory() as d:
  now=[0];a,q,e,l=mk(Path(d),Obs(),lambda *x:{'passed':True});a.clock=lambda:now[0];a.arm();now[0]=151
  try:a.consume('T05thread:1;')
  except TimeoutError:pass
  else:raise AssertionError('deadline accepted')
check('observation_hard_deadline',deadline)
out={'status':'PASS_NO_QEMU_FAKE_LIFECYCLE','fixture':'fake QMP/QEMU/locks/observer; no VM','cases':checks,'count':len(checks),'adapter_sha256':hashlib.sha256((HERE/'observer/execution_adapter.py').read_bytes()).hexdigest()}
(HERE/'tests/adapter-host-tests.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
