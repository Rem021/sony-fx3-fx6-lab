from model_combined import *
import unittest
RUN=Path(sys.argv[1]);sys.argv=sys.argv[:1]
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  RUN.mkdir(mode=0o700);cls.build=D.build(RUN/'built');cls.raw=(RUN/'built/parent-module.so').read_bytes();cls.im=(B/'stage218-fixed-shell-process-filter/originals/im.elf').read_bytes();cls.rows=[];cls.debug=[]
 def run_case(self,name,fault=None,tid=777):
  k=Kernel(self.raw,self.im,fault);k.parent.tid=tid;g=Guest(self.raw,k.parent);self.debug.append((name,k,g));result=g.initialize();g.unload();self.assertFalse(k.source_accesses);self.assertFalse(k.exec_attempts);return k,g,result
 def record(self,name,k,result):self.rows.append(dict(name=name,result=list(result),summary=k.combined_summary()))
 def test_01_same_call_prepare_child_collect_and_all_FDs_close(self):
  for tid in [777,778,779,780]:
   k,g,result=self.run_case('normal-'+str(tid),tid=tid);self.assertEqual(result,(3,0));self.assertEqual(k.own_exit,0);self.assertEqual(k.parent.mask,0x400);self.assertEqual(k.combined_summary()['remaining_new_FDs'],[]);self.assertTrue(k.waits);self.assertTrue(all(x['role']=='own' and x['mask']&(1<<9) for x in k.wait_subjects));self.assertEqual(len(k.clone_events),1);self.record('normal-'+str(tid),k,result)
 def test_02_preparation_failure_even_published_plan_never_starts_child(self):
  for fault in ['short-plan-write','report-write','rename-unsupported','publish-race','post-publish-root-close','expire-after-publish','expire-during-final-close']:
   k,g,result=self.run_case(fault,fault);self.assertEqual(result[0],2);self.assertFalse(k.worker_started);self.assertFalse(k.clone_events);self.record(fault,k,result)
 def test_03_same_creator_signal_can_run_only_after_original_wait(self):
  for fault,expected,old in [('same-creator-after-nonzero',(2,64),68),('same-creator-after-zero',(3,0),0)]:
   k,g,result=self.run_case(fault,fault);self.assertEqual(result,expected);self.assertEqual(k.own_exit,old);self.assertEqual(len(k.creator_signal_events),2);self.assertEqual(k.waits[-1]['status'],old<<8);self.assertTrue(all(x['role']=='own' for x in k.wait_subjects));self.assertEqual(k.parent.mask,0x400);self.record(fault,k,result)
 def test_04_nonzero_bad_creds_or_foreign_other_thread_remain_held(self):
  for fault,expected in [('child-control-close',64),('wrong-DONE-cred',62),('SCM-rights',62),('short-with-rights',62),('foreign-other-thread',63)]:
   k,g,result=self.run_case(fault,fault);self.assertEqual(result,(2,expected));self.assertTrue(k.combined_summary()['rights_all_closed'] if 'rights_all_closed' in k.combined_summary() else all(fd not in k.parent.fds for fd in k.rights));self.record(fault,k,result)
 def test_05_pending_timeout_never_becomes_success_after_late_child_exit(self):
  k,g,result=self.run_case('stall-child','stall-child');self.assertEqual(result,(2,65));self.assertTrue(k.child.alive);self.assertLessEqual(k.parent_sleeps,100);self.assertEqual(k.parent.mask,0x400);k.combined_fault=None;self.assertEqual(k.child.guest.run_child(),0)
  # The module has unloaded. A second load is preparation replay, no observer.
  k.nodes['/tmp/jiritsu/libJit.so'].data[:]=self.raw;again=Guest(self.raw,k.parent);self.assertEqual(again.initialize(),(2,11));again.unload();self.assertEqual(len(k.clone_events),1);self.record('stall-child',k,result)
 def test_06_allocation_or_mask_restore_failure_never_reports_success(self):
  for fault in ['anonymous-allocation','anonymous-executable-permission','parent-mask-restore']:
   k,g,result=self.run_case(fault,fault);self.assertEqual(result[0],2);self.record(fault,k,result)
 def test_07_same_inode_plan_substitution_is_rejected_before_launch(self):
  k,g,result=self.run_case('mutate-plan-between','mutate-plan-between');self.assertEqual(result,(4,0));self.assertTrue(k.plan_mutated);self.assertFalse(k.worker_started);self.assertFalse(k.clone_events);self.record('mutate-plan-between',k,result)
 def test_08_failed_socket_profile_closes_both_owned_ends_before_clone(self):
  k,g,result=self.run_case('socket-profile','socket-profile');self.assertEqual(result,(2,43));self.assertFalse(k.clone_events);self.assertEqual(k.combined_summary()['remaining_new_FDs'],[]);self.record('socket-profile',k,result)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 out=dict(schema='fx3-own-single-constructor-prepare-NOOP-collect-v1',status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),details=[dict(test=str(t),traceback=tb) for t,tb in result.failures+result.errors],build=getattr(Tests,'build',None),cases=Tests.rows,debug=[dict(name=n,errors=g.errors,trace=g.trace[-15:],child_errors=k.own_child.guest.errors if k.own_child else []) for n,k,g in Tests.debug],source_hashes={n:sha256((H/n).read_bytes()).hexdigest() for n in ['combined.c','combined_build.py','core_support.inc','parent_ipc.inc','model_combined.py','test_combined.py']},only_own_ARM64_executed=True,actual_Linux_processes_or_threads_created=False,original_Sony_Linux_or_glibc_executed=False,new_device_operations=0,boot_device_card_or_recording_source_reads=0,signal_callback_gap_between_clone_and_collection_removed_in_model=True,CLONE_PARENT_ptrace_subreaper_and_other_thread_death_adoption_not_modeled=True,actual_service_request_timing_or_target_kernel_verified=False,full_boot_capture_worker_integrated=False,first_flash_released=False,goal_complete=False)
 (RUN/'receipt.json').write_text(json.dumps(out,indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful() else 1)
