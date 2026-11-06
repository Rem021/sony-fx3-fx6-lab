from pathlib import Path
from hashlib import sha256
import json,sys,unittest
import model_receiver as M
H=Path(__file__).resolve().parent;RUN=Path(sys.argv[1]);sys.argv=sys.argv[:1]
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  RUN.mkdir(mode=0o700);cls.parent=(H/'build-parent-v2/parent.elf').read_bytes();cls.collector=(H/'build-collector-v2/collector.elf').read_bytes();cls.obj=H/'build-parent-v2/worker.o';cls.rows=[]
 def case(self,name,fault=None,pfault=None,drive=False):
  r=M.drive_rejected_peer(self.parent,self.collector,self.obj,fault) if drive else M.case(self.parent,self.collector,self.obj,fault,pfault);self.rows.append(dict(name=name,summary=r));self.assertFalse(r['waits']);self.assertTrue(r['host_borrowed_FDs_unchanged']);self.assertTrue(r['own_C_ACK_precedes_inner_worker']);return r
 def test_01_actual_C_receiver_ACK_observer_and_inner_worker_chain(self):
  for f in [None,'reversed-control-order','unpadded-last-rights']:
   r=self.case('normal-'+str(f),f);self.assertEqual(r['result'],11);self.assertEqual(r['producer']['collector_exit_status'],10752);self.assertEqual(r['producer']['own_worker_status'],0);self.assertFalse(r['received_remaining']);self.assertEqual(len(r['ack']),1)
 def test_02_profile_rejection_never_reads_ancillary_or_sends_ACK(self):
  for f in ['channel-no-cloexec','socket-stream','no-passcred','bad-peer-creator','named-socket']:
   r=self.case(f,f);self.assertEqual(r['result'],4);self.assertFalse(r['received_FDs']);self.assertFalse(r['ack']);self.assertIsNone(r['producer']['own_worker_status'])
 def test_03_bad_message_closes_all_identified_installed_rights(self):
  for f in ['wrong-payload','old-HELLO-v1','short-payload','wrong-credential-PID','wrong-UID','wrong-GID','no-rights','no-credentials','duplicate-credentials','two-rights','253-rights','duplicate-receiver-number','payload-truncated','control-truncated','negative-after-installed-rights']:
   r=self.case(f,f);self.assertEqual(r['result'],2);self.assertFalse(r['received_remaining']);self.assertFalse(r['ack']);self.assertIsNone(r['producer']['own_worker_status'])
 def test_04_descriptor_or_ACK_failure_never_returns_success(self):
  for f in ['received-no-cloexec','ACK-send-error','ACK-corrupt','ACK-wrong-parent','received-close-error','channel-close-error']:
   r=self.case(f,f);self.assertEqual(r['result'],2);self.assertFalse(r['received_remaining'])
 def test_05_expiry_and_rejection_remain_nonstarting_even_if_peer_resumes(self):
  for f in ['wrong-payload','late-before-ACK','late-after-ACK']:
   r=self.case('drive-peer-'+f,f,drive=True);self.assertEqual(r['result'],2);self.assertIsNone(r['producer_after_parent_return']['own_worker_status']);self.assertNotEqual(r['producer_after_parent_return']['collector_exit_status'],10752)
 def test_06_no_HELLO_timeout_is_bounded_no_ACK(self):
  r=self.case('no-HELLO','no-HELLO');self.assertEqual(r['result'],2);self.assertFalse(r['ack']);self.assertLessEqual(r['parent_sleeps'],100)
 def test_07_malformed_kernel_header_retains_UNKNOWN_not_fake_cleanup(self):
  r=self.case('unsupported-malformed-kernel-header','malformed-kernel-header');self.assertEqual(r['result'],2);self.assertEqual(r['receiver_state'],6);self.assertTrue(r['received_remaining']);self.assertFalse(r['ack']);self.assertTrue(r['explicit_incomplete_control_cleanup'])
 def test_08_worker_nonzero_and_collector_death_preserve_failure(self):
  for f in ['worker-close-error','SIGKILL-after-DONE','collector-killed']:
   r=self.case('producer-'+f,pfault=f);self.assertEqual(r['result'],2);self.assertNotEqual(r['producer']['collector_exit_status'],10752)
 def test_09_origin_and_closed_domain_counterexamples_are_not_erased(self):
  r=self.case('foreign-origin-boundary','foreign-origin-same-pid');self.assertEqual(r['result'],11);self.assertEqual(r['anchor_origin'],'foreign B same PID/start');self.assertEqual(r['producer']['collector_exit_status'],9);self.assertIsNone(r['producer']['own_worker_status'])
  r=self.case('closed-inner-domain-boundary',pfault='illegal-parent-injection');self.assertEqual(r['result'],11);self.assertEqual(r['producer']['own_worker_status'],17408)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 r=dict(status='NATIVE_RECEIVER_ACK_SCOPED_PASS_WITH_TWO_ORIGIN_DOMAIN_BOUNDARIES' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),details=[dict(test=str(t),traceback=tb) for t,tb in result.failures+result.errors],cases=Tests.rows,
  source_hashes={n:sha256((H/n).read_bytes()).hexdigest() for n in ['parent_receiver.c','collector-ack.c','receiver_build.py','model_receiver.py','test_receiver.py']},parent_sha256=sha256(Tests.parent).hexdigest(),collector_sha256=sha256(Tests.collector).hexdigest(),
  actual_parent_C_receives_and_closes_kernel_modeled_FDs=True,ACK_required_before_inner_worker=True,shared_absolute_expiry_is_still_a_fixed_fixture=True,
  all_original_Linux_VFS_IPC_clock_and_process_operations_are_explicit_fakes=True,only_own_ARM64_executed=True,
  malformed_kernel_control_failure_can_leave_unidentified_FDs_UNKNOWN=True,origin_and_closed_domain_not_yet_proven=True,
  actual_Sony_constructor_clone_anonymous_image_and_plan_binding_implemented=False,full_boot_capture_integrated=False,
  original_Sony_Linux_glibc_or_driver_executed=False,new_device_operations=0,probe_deployable=False,first_flash_released=False)
 (RUN/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful() else 1)
