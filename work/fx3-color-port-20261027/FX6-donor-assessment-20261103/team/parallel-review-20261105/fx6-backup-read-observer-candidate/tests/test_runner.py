#!/usr/bin/env python3
"""Full HostRunner fake end-to-end; no VM/QMP/socket is opened."""
import hashlib,importlib.util,json,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('runner',HERE/'observer/host_runner.py');H=importlib.util.module_from_spec(spec);spec.loader.exec_module(H)
spec2=importlib.util.spec_from_file_location('core',HERE/'observer/observer_core.py');core=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(core)
spec3=importlib.util.spec_from_file_location('stop',HERE/'observer/run_stop_only.py');stop=importlib.util.module_from_spec(spec3);spec3.loader.exec_module(stop)
CP=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic');APP=CP/'grm-fbinit/appFw-future-skip.so';SERIAL=CP/'runs/cp-bind-66ed0f78/serial.log';M=core.choose_appfw(SERIAL.read_bytes(),APP);BIAS=M['ap']['bias']
checks=[]
def check(n,f):f();checks.append(n)
class QMP:
 def __init__(self,stop_fail=False,quit_fail=False):self.calls=[];self.stop_fail=stop_fail;self.quit_fail=quit_fail;self.status='paused';self.closed=False
 def close(self):self.closed=True
 def call(self,c,args=None,deadline=None):
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
 d={'verify_artifacts':lambda:{},'hash_checker':lambda p:(H.baseline_binding.TARGET_SHA if str(p)==str(H.baseline_binding.TARGET) else H.baseline_binding.APP_SHA),'clock':clock,'sleep':lambda x:None,'uuid_checker':lambda:True,'run_root':str(Path(tmp)/'run'),'lock_factory':lambda:l,'launcher':lambda *a:(_ for _ in ()).throw(RuntimeError('launch failed')) if launchfail else e,'qmp_factory':lambda p,deadline=None:q,'rsp_factory':lambda p,deadline=None:r,'mapping_provider':lambda s,d:(_ for _ in ()).throw(RuntimeError('no map')) if mapfail else M,'tls_reader':lambda:0x7f5cfff740,'callback_cancellable':True,'inherited_cleanup':callback or (lambda *a:{'passed':True,'API16_restored':True,'original_bytes_verified':True,'ack_seen':True})}
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
def stop_only_main():
 with tempfile.TemporaryDirectory() as td:
  now=[0];launches=[];called=[]
  def factory(root):
   d,q,e,l,r=deps(td,lambda:now[0],[('0x02cf0214',False),('0x02cf0214',True),('0x02cf0218',False),('0x02cf0218',True)])
   d['run_root']=str(root);d['launcher']=lambda a,b,c:(launches.append(c) or e);d['inherited_cleanup']=lambda *a:(called.append(1) or {'passed':True,'API16_restored':True,'original_bytes_verified':True,'ack_seen':True});return d
  root=Path(td)/'stop-only'
  before=len(launches);assert stop.main([])==2 and len(launches)==before
  assert stop.main(['--approved-token','WRONG','--new-run-approval','--run-root',str(root)],factory)==2 and len(launches)==before
  assert stop.main(['--approved-token',stop.TOKEN,'--run-root',str(root)],factory)==2 and len(launches)==before
  rc=stop.main(['--approved-token',stop.TOKEN,'--new-run-approval','--run-root',str(root)],factory)
  assert rc==0 and len(launches)==1 and not called
  rec=json.loads((root/'receipt.json').read_text());assert rec['two_keys_observed'] and rec['host_cleanup_complete'] and not rec['clean'] and rec['guest_restore_status']=='unknown_not_attempted' and rec['boot_menu_passed'] is False and rec['runtime_evidence'] is False
  # fresh root reuse must not launch again
  assert stop.main(['--approved-token',stop.TOKEN,'--new-run-approval','--run-root',str(root)],factory)==1 and len(launches)==1
check('stop_only_main_gates_launch_once_zero_guest_writes_receipt',stop_only_main)
def stop_only_uuid_and_ownership():
 with tempfile.TemporaryDirectory() as td:
  now=[0];launches=[]
  def base_deps(root):
   d,q,e,l,r=deps(td,lambda:now[0],[]);d['run_root']=str(root);d['launcher']=lambda *a:(launches.append(1) or e);return d
  missing=Path(td)/'missing-root'
  d=base_deps(missing);d['uuid_checker']=lambda:False
  assert stop.main(['--approved-token',stop.TOKEN,'--new-run-approval','--run-root',str(missing)],lambda r:d)==1
  assert not missing.exists() and not launches
  receipt_root=Path(td)/'with-receipt';receipt_root.mkdir();old=b'{"keep":true}\n';(receipt_root/'receipt.json').write_bytes(old);before=__import__('hashlib').sha256(old).hexdigest()
  d=base_deps(receipt_root);d['uuid_checker']=lambda:False
  assert stop.main(['--approved-token',stop.TOKEN,'--new-run-approval','--run-root',str(receipt_root)],lambda r:d)==1
  assert (receipt_root/'receipt.json').read_bytes()==old and __import__('hashlib').sha256((receipt_root/'receipt.json').read_bytes()).hexdigest()==before and not launches
  other=Path(td)/'with-other';other.mkdir();(other/'keep.txt').write_text('keep')
  d=base_deps(other);assert stop.main(['--approved-token',stop.TOKEN,'--new-run-approval','--run-root',str(other)],lambda r:d)==1
  assert sorted(x.name for x in other.iterdir())==['keep.txt'] and not launches
  raise_root=Path(td)/'factory-raise'
  def boom(root):raise RuntimeError('deps failed')
  assert stop.main(['--approved-token',stop.TOKEN,'--new-run-approval','--run-root',str(raise_root)],boom)==1
  assert not raise_root.exists()
check('uuid_failure_rejected_root_and_receipt_preserved_no_launch',stop_only_uuid_and_ownership)
def stop_only_hash_failures():
 with tempfile.TemporaryDirectory() as td:
  now=[0]
  def factory(root,post):
   d,q,e,l,r=deps(td,lambda:now[0],[('0x02cf0214',False),('0x02cf0214',True),('0x02cf0218',False),('0x02cf0218',True)]);d['run_root']=str(root);d['post_hash_checker']=post;return d
  for i,post in enumerate((lambda p:'0'*64, lambda p:(_ for _ in ()).throw(RuntimeError('hash failed')))):
   root=Path(td)/('hash-'+str(i));rc=stop.main(['--approved-token',stop.TOKEN,'--new-run-approval','--run-root',str(root)],lambda r,p=post:factory(r,p));assert rc==1
   rec=json.loads((root/'receipt.json').read_text());assert rec['two_keys_observed'] and rec['host_cleanup_complete'] and rec['verification_failed'] is True and rec['input_unchanged_after'] in (False,None)
check('hash_drift_or_error_exit_nonzero_but_observations_preserved',stop_only_hash_failures)
def cleanup_phase_order():
 with tempfile.TemporaryDirectory() as td:
  seen=[];q=QMP();e=Qemu();l=Locks()
  class R:
   phase='observation'
   def set_phase(self,p):self.phase=p;seen.append('phase:'+p)
   def close(self):seen.append('rsp_close')
  class O:
   possibly=set()
   def cleanup(self):seen.append('observer:'+h.rsp.phase);return {'all_removed':True,'residual':[],'results':[]}
  h=H.HostRunner({'stop_only':True,'run_root':str(Path(td)/'run'),'clock':lambda:0,'uuid_checker':lambda:True,'verify_artifacts':lambda:{},'hash_checker':lambda p:'x','post_hash_checker':lambda p:'x','lock_factory':lambda:l,'launcher':lambda *a:e,'qmp_factory':lambda p,deadline=None:q,'rsp_factory':lambda p,deadline=None:R(),'mapping_provider':lambda *a:{},'tls_reader':lambda:1,'runtime_evidence':False})
  h.qmp=q;h.qemu=e;h.locks=l;h.rsp=R();h.observer=O();h.possibly=set();h.status='observed';h.deadline=H.Deadline(lambda:0)
  h.cleanup()
  assert seen.index('phase:cleanup')<seen.index('observer:cleanup'),seen
check('cleanup_switches_rsp_phase_before_observer_z1',cleanup_phase_order)
def expired_observation_total_cleanup_z1():
 with tempfile.TemporaryDirectory() as td:
  cmds=[]
  class D:
   def remaining_observation(self):return 0
   def remaining_total(self):return 30
   def clamp_total(self,x):return x
  class R:
   def __init__(self):self.phase='observation'
   def set_phase(self,p):self.phase=p
   def command(self,c,args=None,deadline=None):cmds.append(c);return 'OK'
   def close(self):pass
  r=R();q=QMP();e=Qemu();l=Locks()
  o=core.Observer(M,r,lambda:0x7f5cfff740,clock=lambda:0);o.arm()
  h=H.HostRunner({'stop_only':True,'run_root':str(Path(td)/'run'),'clock':lambda:0,'uuid_checker':lambda:True,'verify_artifacts':lambda:{},'hash_checker':lambda p:'x','post_hash_checker':lambda p:'x','lock_factory':lambda:l,'launcher':lambda *a:e,'qmp_factory':lambda p,deadline=None:q,'rsp_factory':lambda p,deadline=None:r,'mapping_provider':lambda *a:M,'tls_reader':lambda:1});h.qmp=q;h.qemu=e;h.locks=l;h.rsp=r;h.observer=o;h.possibly=set(o.possibly);h.status='observed';h.deadline=D()
  out=h.cleanup();assert any(x.startswith('z1,') for x in cmds),cmds;assert r.phase=='cleanup';assert out['breakpoints']['all_removed'];assert out['host_cleanup_complete']
check('expired_observation_total_remaining_z1_sent_before_cleanup',expired_observation_total_cleanup_z1)
def launch_fail():
 with tempfile.TemporaryDirectory() as td:
  now=[0];d,q,e,l,r=deps(td,lambda:now[0],launchfail=True);h=H.HostRunner(d);out=h.run();assert not out['clean'] and l.released
check('partial_launch_failure_cleanup',launch_fail)
out={'status':'PASS_NO_QEMU_FAKE_RUNNER','fixture':'fake launcher/QMP/RSP/locks/process/map/TLS; no VM','cases':checks,'count':len(checks),'runner_sha256':hashlib.sha256((HERE/'observer/host_runner.py').read_bytes()).hexdigest()}
(HERE/'tests/runner-host-tests.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
