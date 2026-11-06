from pathlib import Path
from hashlib import sha256
import json,sys,unittest
import model_observer as M
H=Path(__file__).resolve().parent;RUN=Path(sys.argv[1]);sys.argv=sys.argv[:1]
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  RUN.mkdir(mode=0o700);cls.raw=(H/'build-observer/observer.elf').read_bytes();cls.producer=(H/'build-collector-anchor/collector.elf').read_bytes();cls.rows=[]
 def record(self,name,r):
  self.rows.append(dict(name=name,summary=r));self.assertFalse(r['waits']);self.assertTrue(r['no_numeric_pid_path_lookup_or_wait']);self.assertTrue(r['host_borrowed_FDs_unchanged']);self.assertTrue(r['new_stat_FDs_all_closed'])
 def test_01_same_live_collector_object_sender_worker_exit_and_detachment(self):
  r=M.paired(self.raw,self.producer);self.assertEqual(r['result'],11);self.assertEqual(r['producer']['collector_exit_status'],42<<8);self.assertEqual(r['producer']['own_worker_status'],0);self.assertEqual(len(r['self_proc_anchor_transfers']),1);self.assertTrue(r['same_live_process_object_used_by_both_own_machines']);self.record('same-live-object-pair',r)
 def test_02_real_producer_failure_never_emits_success_sentinel(self):
  for f in ['worker-close-error','SIGKILL-after-DONE','wrong-DONE','collector-killed']:
   r=M.paired(self.raw,self.producer,f);self.assertEqual(r['result'],2);self.assertNotEqual(r['producer']['collector_exit_status'],42<<8);self.record('paired-'+f,r)
 def test_03_zero_is_not_success_even_if_permission_filter_hides_signal(self):
  for f,status in [(None,0),('filtered-zero',9),('filtered-zero',42<<8),(None,9),(None,68<<8)]:
   r=M.case(self.raw,f,status);self.assertEqual(r['result'],2);self.record('wrong-or-filtered-status-'+str(f)+'-'+str(status),r)
 def test_04_numeric_reuse_does_not_redirect_the_old_anchor(self):
  r=M.case(self.raw,'numeric-reuse-after-exit');self.assertEqual(r['result'],11);self.assertTrue(all(x['object']=='original object A' for x in r['lookups']));self.record('reuse-after-evidence',r)
  for f in ['numeric-reuse-before-evidence','gone-before-evidence']:
   r=M.case(self.raw,f);self.assertEqual(r['result'],2);self.record(f,r)
 def test_05_flexible_kernel_comm_and_short_reads(self):
  for f in ['complex-comm','short-chunks','gone-ESRCH']:
   r=M.case(self.raw,f);self.assertEqual(r['result'],11);self.record(f,r)
 def test_06_identity_format_and_descriptor_failures_deny(self):
  for f in ['bad-pid','bad-parent','bad-start','multi-thread','truncated-record','extra-field','exit-overflow','negative-exit','huge-record','read-error','wrong-filesystem','anchor-not-directory','anchor-UID','anchor-replaced','stat-inode-changed','stat-close-error','anchor-close-error','post-sentinel-EACCES']:
   r=M.case(self.raw,f);self.assertIn(r['result'],(2,4));self.record(f,r)
 def test_07_liveness_and_unreaped_zombie_do_not_certify_detachment(self):
  for f in ['live-zero','zombie-only']:
   r=M.case(self.raw,f);self.assertEqual(r['result'],2);self.assertEqual(len(r['lookups']),100);self.record(f,r)
 def test_08_origin_boundary_must_remain_open(self):
  r=M.case(self.raw,'wrong-anchor-same-pid-and-start',9);self.assertEqual(r['result'],11);self.assertEqual(r['collector_kernel_raw_status'],9);self.assertEqual(r['anchor_origin'],'foreign object B');self.record('untrusted-origin-boundary-counterexample',r)
  r=M.paired(self.raw,self.producer,'illegal-parent-injection');self.assertEqual(r['result'],11);self.assertEqual(r['producer']['own_worker_status'],68<<8);self.record('private-child-domain-boundary-counterexample',r)
 def test_09_permission_filtered_real_producer_remains_unknown(self):
  r=M.paired(self.raw,self.producer,observer_fault='filtered-zero');self.assertEqual(r['producer']['collector_exit_status'],42<<8);self.assertEqual(r['result'],2);self.record('paired-filtered-sentinel',r)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 out=dict(status='SCOPED_OBJECT_OBSERVER_PASS_WITH_ANCHOR_ORIGIN_BOUNDARY' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),details=[dict(test=str(t),traceback=tb) for t,tb in result.failures+result.errors],cases=Tests.rows,
   source_hashes={n:sha256((H/n).read_bytes()).hexdigest() for n in ['collector-anchor.c','observer.c','candidate_build.py','model_observer.py','test_observer.py']},observer_sha256=sha256(Tests.raw).hexdigest(),collector_sha256=sha256(Tests.producer).hexdigest(),
   own_two_machine_live_object_pair_executed=True,all_Linux_proc_kernel_permissions_times_tasks_and_detachment_are_explicit_fakes=True,
   original_Sony_Linux_or_glibc_executed=False,actual_Linux_processes_or_threads_created=False,new_device_operations=0,
   self_proc_anchor_sender_implemented=True,parent_native_SCM_receiver_and_authentic_creation_bridge_implemented=False,
   arbitrary_wrong_origin_anchor_can_still_false_complete=True,full_job_or_USB_completion_or_first_flash_released=False,deployable=False)
 (RUN/'receipt.json').write_text(json.dumps(out,indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful() else 1)
