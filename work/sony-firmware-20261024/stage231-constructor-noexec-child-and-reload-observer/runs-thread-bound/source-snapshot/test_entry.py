from model_entry import *
import unittest
RUN=Path(sys.argv[1]);sys.argv=sys.argv[:1]
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  RUN.mkdir(mode=0o700);cls.build=D.build(RUN/'built');cls.raw=(RUN/'built/parent-module.so').read_bytes();cls.im=(H.parent/'stage218-fixed-shell-process-filter/originals/im.elf').read_bytes();cls.cases=[];cls.objects=[]
 def new(self,name,fault=None):
  k=Kernel(self.raw,self.im,fault);g=Guest(self.raw,k.parent)
  if fault=='mapped-image':g.u.mem_write(g.base+0x800,b'\xaa')
  self.objects.append((name,k,g));return k,g
 def start(self,name,fault=None):
  k,g=self.new(name,fault);self.assertEqual(g.initialize(),(1,0));self.assertEqual(k.parent.mask,0x400);g.unload();self.assertTrue(k.child.alive);return k,g
 def observe(self,k):
  k.plan(2);g=Guest(self.raw,k.parent,base=0x40000000);value=g.initialize();g.unload();return value
 def record(self,name,k,values):
  row=k.summary();row.update(name=name,observations=values,constructor_parent_unloaded_before_child_execution=True,no_actual_Linux_or_Sony_code_executed=True);self.cases.append(row)
 def test_01_child_survives_unload_and_next_constructor_proves_exit(self):
  k,g=self.start('normal');self.assertEqual(k.child.guest.run_child(),0);k.im_reap();self.assertFalse(k.reaper[-1]['eligible']);self.assertEqual(self.observe(k),(3,0));self.assertEqual(len(k.waits),1);self.assertEqual(k.waits[0]['options'],0xa0000001);self.assertEqual(k.waits[0]['status'],0);self.assertEqual(len(k.child_FD_sets),1);self.assertEqual(len(k.child_FD_sets[0]),1)
  self.assertEqual(len(k.signal_ops),124);self.assertTrue(all(x['pid']==7001 for x in k.signal_ops));self.assertEqual(k.exec_attempts,[]);self.assertEqual(k.source_accesses,[])
  k.plan(1,nonce=b'\xee'*16);h=Guest(self.raw,k.parent);self.assertEqual(h.initialize(),(2,10));h.unload();self.assertEqual(len(k.clone_events),1);self.record('normal',k,[3])
 def test_02_pending_child_is_unknown_and_single_observer_not_replayed(self):
  k,g=self.start('pending');self.assertEqual(self.observe(k)[0],2);self.assertTrue(k.child.alive);self.assertEqual(k.child.guest.run_child(),0);before=len(k.waits);self.assertEqual(self.observe(k),(2,43));self.assertEqual(len(k.waits),before);self.record('pending',k,[2,2])
 def test_03_external_WALL_waiter_still_causes_ECHILD(self):
  k,g=self.start('other-waiter');self.assertEqual(k.child.guest.run_child(),0);k.im_reap(all_children=True);self.assertTrue(k.reaper[-1]['eligible']);self.assertEqual(self.observe(k)[0],2);self.assertEqual(k.waits[-1]['returned'],-10);self.record('other-waiter',k,[2])
 def test_04_FINISH_like_done_does_not_hide_nonzero_exit(self):
  k,g=self.start('close-after-DONE','child-control-close');self.assertEqual(k.child.guest.run_child(),68);self.assertEqual(self.observe(k)[0],2);self.assertEqual(k.send_events[-1]['kind'],2);self.assertEqual(k.waits[-1]['status'],68<<8);self.record('close-after-DONE',k,[2])
 def test_05_bad_plan_file_or_loaded_bytes_reject_before_clone(self):
  for name in ['bad-plan','image-file','mapped-image']:
   k,g=self.new(name,name);self.assertEqual(g.initialize()[0],4);self.assertEqual(k.clone_events,[]);g.unload();self.record(name,k,[4])
 def test_06_private_credentials_and_rights_reject_and_close(self):
  for name in ['wrong-DONE-cred','SCM-rights','short-with-rights']:
   k,g=self.start(name,name);self.assertEqual(k.child.guest.run_child(),0);self.assertEqual(self.observe(k)[0],2);self.assertTrue(k.summary()['rights_all_closed']);self.record(name,k,[2])
 def test_07_borrowed_control_fd_number_reuse_rejected_before_wait(self):
  k,g=self.start('fd-reuse');self.assertEqual(k.child.guest.run_child(),0);record=k.nodes['/tmp_wbshd/fx3-bootstrap-owner-v1/entry.owner'].data;fd=struct.unpack_from('<I',record,32)[0];k.parent.fds[fd]['desc']=dict(node=Node('wrong socket inode',0o140600),kind='socket',queue=deque(),creator=321);self.assertEqual(self.observe(k),(2,42));self.assertEqual(k.waits,[]);self.record('fd-reuse',k,[2])
 def test_08_parent_mask_restore_failure_never_grants_work(self):
  k,g=self.new('mask-restore','parent-mask-restore');self.assertEqual(g.initialize()[0],2);g.unload();self.assertEqual(k.send_events,[]);self.assertIsNone(k.child.guest.run_child());self.assertTrue(k.child.guest.blocked);self.record('mask-restore',k,[2])
 def test_09_deadline_blocks_work_but_allows_same_child_observation(self):
  k,g=self.new('expired-start');k.clock=902_000_000_000;self.assertEqual(g.initialize()[0],4);self.assertEqual(k.clone_events,[]);g.unload();self.record('expired-start',k,[4])
  k,g=self.start('expired-child');k.clock=902_000_000_000;self.assertEqual(k.child.guest.run_child(),69);self.assertEqual(self.observe(k)[0],2);self.assertEqual(k.waits[-1]['status'],69<<8);self.record('expired-child',k,[2])
  k,g=self.start('expired-observation');self.assertEqual(k.child.guest.run_child(),0);k.clock=902_000_000_000;self.assertEqual(self.observe(k),(3,0));self.record('expired-observation',k,[3])
 def test_10_different_or_reused_creator_thread_rejects_before_wait(self):
  for name,reused in [('other-thread',False),('reused-thread-number',True)]:
   k,g=self.start(name);self.assertEqual(k.child.guest.run_child(),0)
   if reused:k.parent.generation+=1
   else:k.parent.tid=778
   self.assertEqual(self.observe(k),(2,48));self.assertEqual(k.waits,[]);self.record(name,k,[2])
 def test_11_recycled_foreign_clone_PID_cannot_supply_original_exit(self):
  k,g=self.start('PID-reuse-at-wait','PID-reuse-at-wait');self.assertEqual(k.child.guest.run_child(),0);self.assertEqual(self.observe(k)[0],2);self.assertTrue(k.pid_reused);self.assertEqual(k.waits[-1]['returned'],-10);self.record('PID-reuse-at-wait',k,[2])
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 out=dict(schema='fx3-constructor-noexec-reload-lifecycle-model-v1',status='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),details=[dict(test=str(t),traceback=tb) for t,tb in result.failures+result.errors],build=getattr(Tests,'build',None),cases=Tests.cases,debug=[dict(name=n,guest_errors=g.errors,child_errors=k.child.guest.errors if k.child else [],parent_last_syscalls=g.trace[-12:],child_last_syscalls=k.child.guest.trace[-12:] if k.child else []) for n,k,g in Tests.objects],source_hashes={n:sha256((H/n).read_bytes()).hexdigest() for n in ['entry.c','entry_build.py','core_support.inc','parent_ipc.inc','model_entry.py','test_entry.py']},own_ARM64_executed=True,real_processes_or_threads_created=False,original_Sony_or_Linux_code_executed=False,new_camera_operations=0,boot_or_other_source_reads=0,full_boot_capture_worker_integrated=False,actual_FX3_kernel_loader_credentials_or_recovery_verified=False,goal_complete=False,flashable=False)
 (RUN/'receipt.json').write_text(json.dumps(out,indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful() else 1)
