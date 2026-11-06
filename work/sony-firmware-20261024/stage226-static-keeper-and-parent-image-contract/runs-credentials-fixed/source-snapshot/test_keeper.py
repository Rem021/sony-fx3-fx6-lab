from keeper_model import *
import unittest
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  check_volume();RUN.mkdir(mode=0o700);cls.worker_build=WK.build(RUN/'worker-built');cls.keeper_build=KK.build(RUN/'keeper-built');cls.worker=read_file(RUN/'worker-built/worker.elf',4*1024*1024);cls.keeper=read_file(RUN/'keeper-built/worker.elf',4*1024*1024)
  assert cls.worker_build['sha256']==sha256(cls.worker).hexdigest() and cls.keeper_build['sha256']==sha256(cls.keeper).hexdigest()
  cls.source=H.parent/'stage219-bound-handoff-and-request-claims/runs-final-v2/fixture/synthetic.boot';cls.profiles={}
  for path,size,digest in B.FILE_PROFILE:
   data=read_file(R/'work/sony-firmware-20261024/stage213-AP-eMMC-boot-asset-search/originals/current-p3-initrd'/path.lstrip('/'),size);assert sha256(data).hexdigest()==digest;cls.profiles[path]=data
  cls.im=read_file(H.parent/'stage218-fixed-shell-process-filter/originals/im.elf',40920);cls.kernels=[];cls.cases=[]
 def case(self,name,requests=None,fault=None):
  k=KeeperKernel(name,self.source,self.profiles,self.im,self.keeper,self.worker,requests or [B.request('b'*32,'boot0',0)],fault);g=KeeperGuest(self.keeper,k);self.kernels.append(k)
  try:code=g.run_keeper()
  except BaseException:
   self.cases.append(dict(name=name,debug_vm_errors=g.errors,debug_kernel_errors=k.errors,debug_last_trace=g.trace[-8:],debug_events=k.events));raise
  for link in k.links:
   if link.thread.is_alive():link.release_fixture();link.thread.join(timeout=12)
   self.assertFalse(link.thread.is_alive());self.assertEqual(link.errors,[]);self.assertEqual(link.guest.errors,[]);self.assertEqual(link.child.errors,[])
  self.assertEqual(g.errors,[]);self.assertEqual(k.errors,[]);self.assertEqual(k.im_action,0x402f4c);self.assertTrue(all(x['pid']==7001 for x in k.signal_ops))
  self.cases.append(dict(name=name,code=code,keeper_syscalls=len(g.trace),keeper_last_syscall=g.trace[-1]['number'],host_results=k.host_results,signal_ops=k.signal_ops,im_action_unchanged=k.im_action==0x402f4c,im_reaper_attempts=k.im_reaper_attempts,worker_returns=[l.child_return for l in k.links],source_reads=[len(l.child.source_reads) for l in k.links],worker_FDs=[x['live_FDs'] for x in k.execs],kernel_exit_cleanup=k.exit_closed,events=k.events))
  return k,g,code
 def test_01_standalone_keeper_and_worker_complete_under_active_im_reaper(self):
  k,g,code=self.case('normal');self.assertEqual(code,0);self.assertEqual([r['state'] for r in k.host_results],[0,0]);self.assertEqual([l.child_return for l in k.links],[0]);self.assertEqual(len(k.links[0].child.source_reads),2);self.assertTrue(k.im_reaper_attempts);self.assertTrue(all(not x['eligible'] for x in k.im_reaper_attempts));self.assertEqual(k.exit_closed,[])
 def test_02_own_signal_reset_or_verification_failure_never_launches(self):
  for fault in ['signal-error','signal-query']:
   k,g,code=self.case(fault,fault=fault);self.assertEqual(code,81);self.assertFalse(k.links)
 def test_03_host_task_SHA_or_credentials_rejected_before_source(self):
  for fault in ['job-keeper-hash','host-credentials']:
   k,g,code=self.case(fault,fault=fault);self.assertEqual(code,83);self.assertFalse(k.links)
 def test_04_worker_checks_parent_contents_beyond_metadata(self):
  k,g,code=self.case('worker-parent-data',fault='worker-parent-data');self.assertEqual(code,85);self.assertEqual([l.child_return for l in k.links],[44]);self.assertEqual([len(l.child.source_reads) for l in k.links],[0]);self.assertEqual([r['state'] for r in k.host_results],[2])
 def test_05_all_four_windows_same_live_keeper(self):
  requests=[B.request('e'*32,'boot1',i,0 if i==0 else B.MAX_BOOT) for i in range(4)];k,g,code=self.case('full',requests=requests);self.assertEqual(code,0);self.assertEqual([len(l.child.source_reads) for l in k.links],[128,128,128,126]);self.assertEqual(len(k.host_results),5)
  d=B.assemble_windows([l.child.output for l in k.links],[0]*4,RUN/'assembled','1'*64);self.assertEqual(d['sha256'],sha256(self.source.read_bytes()).hexdigest())
 def test_06_finish_response_is_not_sufficient_when_close_fails(self):
  k,g,code=self.case('finish-close',fault='finish-close');self.assertEqual(code,89);self.assertEqual(k.host_results[-1]['operation'],2);self.assertEqual(k.host_results[-1]['state'],0);self.assertFalse(k.host_results[-1]['actual_keeper_exit_observed'])
 @classmethod
 def tearDownClass(cls):
  for k in cls.kernels:
   for link in k.links:
    if link.thread.is_alive():link.release_fixture();link.thread.join(timeout=12)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 report=dict(schema='fx3-own-static-keeper-worker226-model-tests-v1',status='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),details=[dict(test=str(t),traceback=tb) for t,tb in result.failures+result.errors],cases=Tests.cases,worker_build=Tests.worker_build,keeper_build=Tests.keeper_build,all_model_threads_terminal=all(not l.thread.is_alive() for k in Tests.kernels for l in k.links),source_hashes={str(p.relative_to(H)):sha256(p.read_bytes()).hexdigest() for p in list((H/'worker').glob('*.c'))+list((H/'worker').glob('*.inc'))+list((H/'keeper').glob('*.c'))+list((H/'keeper').glob('*.inc'))+[H/'protocol.py',H/'keeper_model.py',H/'test_keeper.py',H/'worker/static_build.py',H/'keeper/static_build.py']},own_keeper_and_worker_static_start_to_exit_executed=True,original_Sony_or_Linux_kernel_or_glibc_executed=False,actual_bootstrap_native_loader_upload_credentials_signals_or_recovery_verified=False,new_camera_operations=0,hardware_validated=False,independent_recovery_proven=False,flashable=False)
 new_directory(RUN/'receipt',{'results.json':encode(report)});raise SystemExit(0 if result.wasSuccessful() else 1)
