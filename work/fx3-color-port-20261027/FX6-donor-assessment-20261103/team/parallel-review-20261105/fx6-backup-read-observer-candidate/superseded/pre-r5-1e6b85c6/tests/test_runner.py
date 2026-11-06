#!/usr/bin/env python3
"""Full HostRunner fake end-to-end; no VM/QMP/socket is opened."""
import hashlib,importlib.util,json,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('runner',HERE/'observer/host_runner.py');H=importlib.util.module_from_spec(spec);spec.loader.exec_module(H)
spec2=importlib.util.spec_from_file_location('core',HERE/'observer/observer_core.py');core=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(core)
CP=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic');APP=CP/'grm-fbinit/appFw-future-skip.so';SERIAL=CP/'runs/cp-bind-66ed0f78/serial.log';M=core.choose_appfw(SERIAL.read_bytes(),APP);BIAS=M['ap']['bias']
checks=[]
def check(n,f):f();checks.append(n)
class QMP:
 def __init__(self,stop_fail=False,quit_fail=False):self.calls=[];self.stop_fail=stop_fail;self.quit_fail=quit_fail;self.status='paused';self.closed=False
 def close(self):self.closed=True
 def call(self,c):
  self.calls.append(c)
  if c=='stop' and self.stop_fail:raise TimeoutError('qmp stop timeout')
  if c=='quit' and self.quit_fail:raise TimeoutError('qmp quit timeout')
  if c=='query-status':return {'status':self.status,'running':self.status=='running'}
  return {}
class Qemu:
 def __init__(self,wait_fail=False):self.waited=0;self.killed=False;self.terminated=False;self.wait_fail=wait_fail;self.returncode=0
 def wait(self,timeout):
  self.waited+=1
  self.returncode=0
  if self.wait_fail:raise TimeoutError('still alive')
  return 0
 def terminate(self):self.terminated=True
 def kill(self):self.killed=True
class Locks:
 def __init__(self,release_fail=False):self.released=False;self.acquired=False;self.release_fail=release_fail
 def acquire(self):self.acquired=True
 def release(self):
  if self.release_fail:raise OSError('lock release failed')
  self.released=True
class RSPF:
 def __init__(self,stops,clock):self.stops=list(stops);self.clock=clock;self.ret=False;self.key=None;self.needs_resume=False
 def select_thread(self,s):return '241'
 def regs(self):
  k=core.KEYS[0] if self.key is None else next(x for x in core.KEYS if x['name']==self.key);fp=0x7ed3d12290;buf=fp+k['slot_off'];r=[0]*33;r[29]=fp
  if not self.ret:r[0]=buf;r[30]=BIAS+k['return_va'];r[32]=BIAS+k['thunk_va']
  else:r[0]=0xfffffc03;r[32]=BIAS+k['return_va']
  return tuple(r)
 def virtual_read(self,addr,size):
  k=core.KEYS[0] if self.key is None else next(x for x in core.KEYS if x['name']==self.key);fp=0x7ed3d12290;buf=fp+k['slot_off']
  if addr==BIAS+k['thunk_va']:return bytes.fromhex(k['thunk_word'])
  if addr==BIAS+k['return_va']:return bytes.fromhex(k['return_word'])
  if addr==buf:return b'\x01\x00\x00\x00' if not self.ret else b'\x16\x16\x16\x16'
  va=addr-BIAS
  for s in core.elf_loads(APP):
   if s['va']<=va and va+size<=s['va']+s['filesz']:
    b=APP.read_bytes();return b[s['fileoff']+va-s['va']:s['fileoff']+va-s['va']+size]
  raise ValueError('unmapped')
 def poll_stop(self,timeout):
  if self.needs_resume or not self.stops:return None
  self.key,self.ret=self.stops.pop(0);self.needs_resume=True
  return 'T05thread:241;'
 def close(self):self.closed=True
 def send_continue(self,timeout=2.0):
  self.needs_resume=False;return {'command':'c','ack':'+','timeout':timeout}
 def command(self,*a,**k):return 'OK'
def deps(tmp,clock,stops=None,wait_fail=False,stop_fail=False,mapfail=False,launchfail=False,callback=None,quit_fail=False,release_fail=False):
 q=QMP(stop_fail,quit_fail);e=Qemu(wait_fail);l=Locks(release_fail);r=RSPF(stops or [],clock)
 d={'verify_artifacts':lambda:{},'hash_checker':lambda p:(H.baseline_binding.TARGET_SHA if str(p)==str(H.baseline_binding.TARGET) else H.baseline_binding.APP_SHA),'clock':clock,'sleep':lambda x:None,'uuid_checker':lambda:True,'run_root':str(Path(tmp)/'run'),'lock_factory':lambda:l,'launcher':lambda *a:(_ for _ in ()).throw(RuntimeError('launch failed')) if launchfail else e,'qmp_factory':lambda p:q,'rsp_factory':lambda p:r,'mapping_provider':lambda s,d:(_ for _ in ()).throw(RuntimeError('no map')) if mapfail else M,'tls_reader':lambda:0x7f5cfff740,'callback_cancellable':True,'inherited_cleanup':callback or (lambda *a:{'passed':True,'API16_restored':True,'original_bytes_verified':True,'ack_seen':True})}
 return d,q,e,l,r
def normal():
 with tempfile.TemporaryDirectory() as td:
  now=[0];d,q,e,l,r=deps(td,lambda:now[0],[('0x02cf0214',False),('0x02cf0214',True),('0x02cf0218',False),('0x02cf0218',True)])
  h=H.HostRunner(d);out=h.run();assert out['clean'] and out['status']=='observed' and len(out['records'])==2 and q.calls[:4]==['query-status','cont','stop','query-status'], {'out':out,'calls':q.calls,'released':l.released,'waited':e.waited}
  assert l.released and e.waited
check('full_runner_normal_two_keys_clean',normal)
def false_inherited_observed():
 with tempfile.TemporaryDirectory() as td:
  now=[0];cb=lambda *a:{'passed':False,'API16_restored':False,'original_bytes_verified':False,'ack_seen':False}
  d,q,e,l,r=deps(td,lambda:now[0],[('0x02cf0214',False),('0x02cf0214',True),('0x02cf0218',False),('0x02cf0218',True)],callback=cb)
  h=H.HostRunner(d);out=h.run();assert not out['clean'] and out['status']=='observed' and 'inherited_contract_not_satisfied' in ' '.join(out['cleanup']['errors'])
check('observed_callback_false_not_clean',false_inherited_observed)
def false_inherited_wait_timeout():
 with tempfile.TemporaryDirectory() as td:
  now=[0];cb=lambda *a:{'passed':False,'API16_restored':False,'original_bytes_verified':False,'ack_seen':False};d,q,e,l,r=deps(td,lambda:now[0],[('0x02cf0214',False)],wait_fail=True,callback=cb);d['sleep']=lambda x:now.__setitem__(0,now[0]+x)
  h=H.HostRunner(d);out=h.run();assert not out['clean'] and not l.released and out['cleanup']['status']=='unclean';assert 'inherited_contract_not_satisfied' in out['cleanup']['errors'] or 'qemu_wait_timeout' in out['cleanup']['errors']
check('false_inherited_and_wait_timeout_not_clean_lock_retained',false_inherited_wait_timeout)
def stop_raises_fallback():
 with tempfile.TemporaryDirectory() as td:
  now=[0];d,q,e,l,r=deps(td,lambda:now[0],[],stop_fail=True);d['sleep']=lambda x:now.__setitem__(0,now[0]+x);h=H.HostRunner(d);out=h.run();assert not out['clean'] and 'qmp_stop_or_query' in ' '.join(out['cleanup']['errors']);assert l.released and e.waited
check('qmp_stop_exception_fallback_no_clean',stop_raises_fallback)
def no_map():
 with tempfile.TemporaryDirectory() as td:
  now=[0];d,q,e,l,r=deps(td,lambda:now[0],mapfail=True);h=H.HostRunner(d);out=h.run();assert not out['clean'] and out['error'] and l.released, {'out':out,'released':l.released}
check('no_current_map_unknown',no_map)
def no_hit():
 with tempfile.TemporaryDirectory() as td:
  now=[0];d,q,e,l,r=deps(td,lambda:now[0],[]);d['sleep']=lambda x:now.__setitem__(0,now[0]+60);h=H.HostRunner(d);out=h.run();assert not out['clean'] and out['error'] and l.released
check('no_hit_deadline_unknown',no_hit)
def callback_timeout():
 with tempfile.TemporaryDirectory() as td:
  now=[0];import time
  d,q,e,l,r=deps(td,lambda:now[0],[('0x02cf0214',False),('0x02cf0214',True),('0x02cf0218',False),('0x02cf0218',True)])
  d['callback_cancellable']=False;d['inherited_cleanup']=lambda *a:(time.sleep(.5) or {'passed':True,'API16_restored':True,'original_bytes_verified':True,'ack_seen':True})
  h=H.HostRunner(d);out=h.run();assert not out['clean'] and ('callback_not_cancellable' in ' '.join(out['cleanup']['errors']) or out['cleanup']['inherited']=='callback_not_cancellable_not_run')
check('inherited_callback_timeout_not_clean',callback_timeout)
def quit_failure():
 with tempfile.TemporaryDirectory() as td:
  now=[0];d,q,e,l,r=deps(td,lambda:now[0],[('0x02cf0214',False),('0x02cf0214',True),('0x02cf0218',False),('0x02cf0218',True)],quit_fail=True);h=H.HostRunner(d);out=h.run();assert not out['clean'] and 'qmp_quit' in ' '.join(out['cleanup']['errors'])
check('qmp_quit_failure_not_clean',quit_failure)
def release_failure():
 with tempfile.TemporaryDirectory() as td:
  now=[0];d,q,e,l,r=deps(td,lambda:now[0],[('0x02cf0214',False),('0x02cf0214',True),('0x02cf0218',False),('0x02cf0218',True)],release_fail=True);h=H.HostRunner(d);out=h.run();assert not out['clean'] and not out['cleanup']['lock_released'] and 'lock_release' in ' '.join(out['cleanup']['errors'])
check('lock_release_failure_not_clean',release_failure)
def stop_only():
 with tempfile.TemporaryDirectory() as td:
  now=[0];called=[];d,q,e,l,r=deps(td,lambda:now[0],[('0x02cf0214',False),('0x02cf0214',True),('0x02cf0218',False),('0x02cf0218',True)])
  d['stop_only']=True;d['inherited_cleanup']=lambda *a:called.append(1) or {'passed':True,'API16_restored':True,'original_bytes_verified':True,'ack_seen':True}
  h=H.HostRunner(d);out=h.run();assert out['two_keys_observed'] and out['host_cleanup_complete'] and not out['clean'] and out['guest_restore_status']=='unknown_not_attempted' and not called
check('stop_only_separates_observation_host_cleanup_guest_restore',stop_only)
def launch_fail():
 with tempfile.TemporaryDirectory() as td:
  now=[0];d,q,e,l,r=deps(td,lambda:now[0],launchfail=True);h=H.HostRunner(d);out=h.run();assert not out['clean'] and l.released
check('partial_launch_failure_cleanup',launch_fail)
out={'status':'PASS_NO_QEMU_FAKE_RUNNER','fixture':'fake launcher/QMP/RSP/locks/process/map/TLS; no VM','cases':checks,'count':len(checks),'runner_sha256':hashlib.sha256((HERE/'observer/host_runner.py').read_bytes()).hexdigest()}
(HERE/'tests/runner-host-tests.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
