from bootstrap_model import *
import unittest
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  check_volume();RUN.mkdir(mode=0o700);cls.build=D.build(RUN/'built');cls.raw=read_file(RUN/'built/parent-module.so',4*1024*1024)
  old=H.parent/'stage226-static-keeper-and-parent-image-contract/runs-final';cls.keeper=read_file(old/'keeper-built/worker.elf',4*1024*1024);cls.worker=read_file(old/'worker-built/worker.elf',4*1024*1024)
  cls.source=H.parent/'stage219-bound-handoff-and-request-claims/runs-final-v2/fixture/synthetic.boot';cls.profiles={}
  for path,size,digest in B.FILE_PROFILE:
   data=read_file(R/'work/sony-firmware-20261024/stage213-AP-eMMC-boot-asset-search/originals/current-p3-initrd'/path.lstrip('/'),size);assert sha256(data).hexdigest()==digest;cls.profiles[path]=data
  cls.im=read_file(H.parent/'stage218-fixed-shell-process-filter/originals/im.elf',40920);cls.cases=[];cls.objects=[]
 def make(self,name,requests=None,fault=None,ram=None):
  reqs=[B.request('b'*32,'boot0',0)] if requests is None else requests;k=BridgeKernel(name,self.source,self.profiles,self.im,self.keeper,self.worker,reqs,fault,ram);g=BridgeGuest(self.raw,k)
  self.assertEqual(g.step(),5);self.assertEqual(g.trace,[]);g.init();self.assertEqual(g.status(),0);self.assertEqual(g.trace,[]);self.objects.append((name,k,g));return k,g
 def drive(self,g):
  until=time.monotonic()+90
  while time.monotonic()<until:
   state=g.step()
   if state in (2,3,4):return state
   time.sleep(.005)
  self.fail('same bootstrap chain did not reach a terminal observation')
 def record(self,name,k,g,state):
  if k.link.thread is not None:k.link.thread.join(timeout=25)
  self.assertTrue(k.link.thread is None or not k.link.thread.is_alive());self.assertEqual(g.errors,[]);self.assertEqual(k.errors,[]);self.assertEqual(k.link.errors,[])
  for keeper in k.keepers:
   for l in keeper.links:self.assertFalse(l.thread.is_alive());self.assertEqual(l.errors,[])
  for fd,flags in k.context_flags.items():self.assertEqual(k.fds[fd].get('flags',1),flags)
  self.cases.append(dict(name=name,state=state,keeper_return=k.link.child_return,keeper_exit_status=k.link.exit_status if k.link.finished else None,waits=k.waits,im_reaper=k.reaper,results=[{key:(value.hex() if isinstance(value,bytes) else value) for key,value in x.items()} for x in k.received_results],sent_jobs=len(k.sent_jobs),clones=k.clones,worker_returns=[l.child_return for q in k.keepers for l in q.links],source_reads=[len(l.child.source_reads) for q in k.keepers for l in q.links],constructor_syscalls=0,zero_argument_calls_use_poisoned_x0_x7=True,parent_FD_flags_unchanged=True,parent_errors=g.errors))
 def test_01_noarg_factory_bootstrap_only_no_source(self):
  k,g=self.make('startup',requests=[]);self.assertEqual(g.step(),1,g.errors);state=self.drive(g);self.assertEqual(state,3,k.link.errors);self.record('startup',k,g,state);self.assertEqual(k.link.child_return,0);self.assertEqual(k.keepers[0].links,[])
 def test_02_one_job_from_module_through_keeper_and_worker(self):
  k,g=self.make('one-job');self.assertEqual(g.step(),1,g.errors);state=self.drive(g);self.assertEqual(state,3,k.link.errors);self.record('one-job',k,g,state);self.assertEqual([len(l.child.source_reads) for l in k.keepers[0].links],[2]);self.assertEqual(len(k.received_results),2)
 def test_03_invalid_or_missing_plan_and_wrong_image_reject_before_clone(self):
  for fault in ['bad-plan','missing-plan','image-byte','non-main-thread']:
   k,g=self.make(fault,fault=fault);self.assertEqual(g.step(),4,g.errors);self.assertEqual(k.clones,[]);self.record(fault,k,g,4)
 def test_04_FINISH_state0_and_keeper_exit89_is_held(self):
  k,g=self.make('keeper-close',fault='keeper-close');self.assertEqual(g.step(),1,g.errors);state=self.drive(g);self.assertEqual(state,2);self.record('keeper-close',k,g,state);self.assertEqual(k.received_results[-1]['operation'],2);self.assertEqual(k.received_results[-1]['state'],0);self.assertEqual(k.link.child_return,89)
 def test_05_reference_im_reaper_still_blocks_outer_exit_proof(self):
  k,g=self.make('outer-reaper',fault='outer-reaper');self.assertEqual(g.step(),1,g.errors);state=self.drive(g);self.assertEqual(state,2);self.record('outer-reaper',k,g,state);self.assertEqual(k.link.child_return,0);self.assertTrue(k.reaper);self.assertTrue(any(x['returned']==-10 for x in k.waits))
  before=(len(k.clones),len(k.sent_jobs));self.assertEqual(g.step(),2);self.assertEqual(before,(len(k.clones),len(k.sent_jobs)))
  q,h=self.make('new-loader',ram=k.ram_path);self.assertEqual(h.step(),2);self.assertEqual(q.clones,[]);self.record('new-loader',q,h,2)
 def test_06_four_windows_serialized_by_same_module_and_keeper(self):
  reqs=[B.request('e'*32,'boot1',i,0 if i==0 else B.MAX_BOOT) for i in range(4)];k,g=self.make('full',requests=reqs);self.assertEqual(g.step(),1,g.errors);state=self.drive(g);self.assertEqual(state,3,k.link.errors);self.record('full',k,g,state)
  links=k.keepers[0].links;self.assertEqual([len(l.child.source_reads) for l in links],[128,128,128,126]);r=B.assemble_windows([l.child.output for l in links],[0]*4,RUN/'assembled','1'*64);self.assertEqual(r['sha256'],sha256(self.source.read_bytes()).hexdigest())
 @classmethod
 def tearDownClass(cls):
  for name,k,g in cls.objects:
   if k.link.thread is not None and k.link.thread.is_alive():
    with k.link.condition:k.link.condition.notify_all()
    k.link.thread.join(timeout=25)
   for fd,row in k.fds.items():
    if row['real'] is not None and fd not in k.closed:os.close(row['real']);k.closed.append(fd)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 r=dict(schema='fx3-noarg-bootstrap-keeper-handoff-model-v1',status='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),details=[dict(test=str(t),traceback=tb) for t,tb in result.failures+result.errors],cases=Tests.cases,debug_instances=[dict(name=n,keeper_return=k.link.child_return,keeper_errors=k.link.errors,worker_returns=[l.child_return for q in k.keepers for l in q.links],worker_errors=[l.errors for q in k.keepers for l in q.links],results=[(x['operation'],x['state'],x['reason']) for x in k.received_results]) for n,k,g in Tests.objects],build=Tests.build,all_model_threads_terminal=all(k.link.thread is None or not k.link.thread.is_alive() for n,k,g in Tests.objects),source_hashes={p.name:sha256(p.read_bytes()).hexdigest() for p in [H/'bootstrap.c',H/'parent_ipc.inc',H/'child_exec.inc',H/'receive_result.inc',H/'dynparent.py',H/'bootstrap_model.py',H/'test_bootstrap.py']},own_three_program_ARM64_chain_executed=True,Sony_loader_or_Linux_kernel_executed=False,real_dispatcher_or_native_load_auth_upload_or_camera_recovery_verified=False,new_camera_operations=0,hardware_validated=False,independent_recovery_proven=False,flashable=False)
 new_directory(RUN/'receipt',{'results.json':encode(r)});raise SystemExit(0 if result.wasSuccessful() else 1)
