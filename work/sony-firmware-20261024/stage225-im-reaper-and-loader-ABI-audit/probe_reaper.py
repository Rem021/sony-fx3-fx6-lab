"""Own224 ARM64 under two explicit wait schedules; never run original im code."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,struct,sys,time,unittest
H=Path(__file__).resolve().parent;R=H.parents[2];RUN=Path(sys.argv[1]);sys.argv=sys.argv[:2]
p=H.parent/'stage224-controlled-launcher-and-preexec-image-pin/test_launcher.py';sys.path.insert(0,str(p.parent))
s=importlib.util.spec_from_file_location('own224tests_for225',p);T=importlib.util.module_from_spec(s);sys.modules[s.name]=T;s.loader.exec_module(T)
Original=T.ParentKernel
class ReaperKernel(Original):
 def __init__(self,*args,**kw):
  super().__init__(*args,**kw);self.reaper_enabled=self.namespace.name.startswith('reaper-');self.reference_reaper=[]
 def wait4(self,u,args):
  # Explicit schedule: original im handler wins after the same child exits,
  # before this own parent core can consume its wait status.
  if self.reaper_enabled and self.link.finished and not self.link.reaped:
   self.reference_reaper.append(dict(operation='modeled im waitpid(-1,status,WNOHANG)',pid_argument=-1,options=1,returned=self.link.child_pid,status=self.link.exit_status))
   self.link.reaped=True
  return super().wait4(u,args)
T.ParentKernel=ReaperKernel
T.Tests.setUpClass();x=T.Tests();records=[]
try:
 for name,expected in [('baseline',0),('reaper-race',2)]:
  q=x.pair(name);assert x.launch(q)==1;q['l'].thread.join(timeout=.001);state=x.drive(q);assert state==expected;q['l'].thread.join(timeout=12);x.finish(q,state)
  k,g,l=q['k'],q['g'],q['l'];assert l.child_return==0 and l.exit_status==0 and l.child_packets==[2,4] and len(l.child.source_reads)==2
  rec=dict(name=name,state=state,parent_module_sha256=sha256(x.raw).hexdigest(),child_return=l.child_return,raw_exit_status=l.exit_status,child_packets=l.child_packets,source_reads=len(l.child.source_reads),clones=k.clones,model_reaper=k.reference_reaper,own_wait_returns=[row['returned'] for row in k.waits],parent_errors=g.errors,child_errors=l.guest.errors)
  if name=='reaper-race':
   assert len(k.reference_reaper)==1 and -10 in rec['own_wait_returns'];before=(len(k.clones),len(k.stages),len(k.execs),list(l.parent_packets))
   assert g.launch(q['hand'],q['req'])==2;assert before==(len(k.clones),len(k.stages),len(k.execs),list(l.parent_packets));rec['same_owner_relaunch_denied_without_new_activity']=True
   z=x.pair('new-owner',namespace=k.namespace,ram=k.ram_path);assert x.launch(z)==2;x.finish(z,2);assert not z['k'].clones and z['k'].events==['reserve-session'];rec['new_owner_cannot_reclaim']=True
  records.append(rec)
finally:T.Tests.tearDownClass()
report=dict(schema='fx3-im-reaper-schedule-counterexample-own224-v1',status='COUNTEREXAMPLE_REPRODUCED_SAFE_HOLD_NO_AVAILABILITY_PROOF',records=records,
 new_own_ARM64_schedules=2,existing_source_tests_not_rerun=True,all_fixture_threads_terminal=all(q['l'].thread is None or not q['l'].thread.is_alive() for q in T.Tests.instances),
 own_parent_child_ARM64_executed=True,Sony_im_handler_or_Linux_kernel_executed=False,model_wait_schedule_is_declared_not_camera_observation=True,
 probe_source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),reused_helpers={str(p.relative_to(R)):sha256(p.read_bytes()).hexdigest() for p in [p,p.parent/'launch_model.py']},
 new_camera_operations=0,hardware_validated=False,independent_recovery_proven=False,flashable=False)
T.new_directory(RUN/'receipt',{'reaper-probe.json':T.encode(report)});print(json.dumps(dict(status=report['status'],states=[z['state'] for z in records],child_returns=[z['child_return'] for z in records],real_camera_operations=0)))
