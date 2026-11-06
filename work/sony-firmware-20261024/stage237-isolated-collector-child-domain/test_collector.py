from pathlib import Path
from hashlib import sha256
import json,sys,unittest
import model_collector as M
H=Path(__file__).resolve().parent;RUN=Path(sys.argv[1]);sys.argv=sys.argv[:1]
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  RUN.mkdir(mode=0o700);cls.raw=(H/'build-current/collector.elf').read_bytes();cls.rows=[];cls.debug=[]
  assert sha256(cls.raw).hexdigest()==json.loads((H/'build-current/build.json').read_text())['sha256']
 def case(self,fault):
  r=M.case(self.raw,fault);self.rows.append(r);self.assertFalse(r['source_accesses']);self.assertTrue(r['host_borrowed_FDs_unchanged']);self.assertTrue(r['only_collector_created_child']);return r
 def test_01_empty_worker_exact_exit_and_race_after_first_recv(self):
  for f in [None,'between-recv-wait']:
   r=self.case(f);self.assertEqual(r['collector_exit_status'],10<<8);self.assertEqual(r['own_worker_status'],0);self.assertTrue(r['worker_reaped']);self.assertFalse(r['collector_remaining_FDs']);self.assertTrue(all(w['eligible_roles']==['own worker'] for w in r['waits'] if w['returned']>0))
 def test_02_preflight_rejects_non_private_initial_context(self):
  for f in ['multi-thread','tid-mismatch','subreaper','traced','unblocked','existing-child','status-open','prctl-unavailable']:
   r=self.case(f);self.assertEqual(r['collector_exit_status'],4<<8);self.assertIsNone(r['own_worker_status']);self.assertFalse(any(x['event']=='clone0' for x in r['events']))
 def test_03_real_nonzero_or_signaled_exit_cannot_be_replaced_by_DONE(self):
  for f,status in [('worker-close-error',68<<8),('SIGKILL-after-DONE',9)]:
   r=self.case(f);self.assertEqual(r['collector_exit_status'],2<<8);self.assertEqual(r['own_worker_status'],status);self.assertTrue(r['worker_reaped'])
 def test_04_bad_private_messages_and_final_own_close_stay_failed(self):
  for f in ['wrong-DONE','SCM-rights','GO-send-error','collector-close-error']:
   r=self.case(f);self.assertEqual(r['collector_exit_status'],2<<8);self.assertTrue(r['injected_rights_all_closed'])
 def test_05_timeout_is_sticky_and_live_child_is_not_abandoned(self):
  r=self.case('stall');self.assertTrue(r['collector_alive']);self.assertTrue(r['own_worker_alive']);self.assertEqual(r['collector_state'],2);self.assertIsNone(r['collector_exit_status'])
  r=self.case('late-zero');self.assertEqual(r['own_worker_status'],0);self.assertEqual(r['collector_exit_status'],2<<8);self.assertEqual(r['collector_state'],2)
 def test_06_external_reap_and_valid_external_parent_reuse_do_not_match(self):
  for f in ['external-reap-cousin','external-reap-host-child']:
   r=self.case(f);self.assertEqual(r['own_worker_status'],68<<8);self.assertTrue(r['collector_alive']);self.assertIsNone(r['collector_exit_status']);self.assertEqual(r['collector_state'],2);self.assertTrue(all('foreign replacement' not in x['eligible_roles'] for x in r['waits']))
 def test_07_collector_death_does_not_report_inner_success(self):
  r=self.case('collector-killed');self.assertEqual(r['collector_exit_status'],9);self.assertNotEqual(r['collector_state'],10)
 def test_08_boundary_counterexample_is_preserved_not_used_as_admission(self):
  r=self.case('illegal-parent-injection');self.assertEqual(r['own_worker_status'],68<<8);self.assertEqual(r['collector_exit_status'],10<<8);self.assertTrue(any(x.get('closed_tree_contract_violated') for x in r['events']))
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 rows=Tests.rows;out=dict(status='SCOPED_CHECKS_PASS_WITH_REQUIRED_CLOSED_DOMAIN_BOUNDARY' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),details=[dict(test=str(t),traceback=tb) for t,tb in result.failures+result.errors],cases=rows,
  source_hashes={p:sha256((H/p).read_bytes()).hexdigest() for p in ['collector.c','isolated_build.py','model_collector.py','test_collector.py']},binary_sha256=sha256(Tests.raw).hexdigest(),
  illegal_same_parent_injection_still_false_completes=True,closed_child_domain_is_required_not_optional=True,
  outer_bootstrap_parent_exit_binding_and_host_completion_implemented=False,probe_deployable=False,
  only_own_ARM64_executed=True,actual_Linux_processes_or_threads_created=False,original_Sony_Linux_glibc_or_driver_executed=False,
  new_device_operations=0,full_boot_source_reading_integrated=False,all16_target_requirements_unchanged=True,first_flash_released=False)
 (RUN/'receipt.json').write_text(json.dumps(out,indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful() else 1)
