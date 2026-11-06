from pathlib import Path
from hashlib import sha256
import json,struct,sys,unittest,zlib
import model_bridge as M
H=Path(__file__).resolve().parent;RUN=Path(sys.argv[1]);sys.argv=sys.argv[:1]
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):RUN.mkdir(mode=0o700);cls.raw=(H/'build-first/bridge.elf').read_bytes();cls.rows=[]
 def case(self,name,**kwargs):
  r=M.case(self.raw,**kwargs);self.rows.append(dict(name=name,summary=r));self.assertTrue(r['borrowed_FDs_unchanged']);self.assertFalse(r['source_accesses']);self.assertFalse(r['root_remaining_anonymous']);return r
 def test_01_real_C_channel_create_clone_private_handoff_and_cleanup(self):
  for pid,tid,cpid,wid,base,clock in [(321,777,5001,7002,0x30000000,1_000_000_000),(9011,9022,11001,12001,0x20000000,100_000_000_000),(400,400,410,420,0x60000000,900_000_000_000)]:
   r=self.case('normal-'+str(pid),pid=pid,tid=tid,child_pid=cpid,worker_pid=wid,base=base,clock=clock);self.assertEqual(r['result'],11);self.assertEqual(r['collector_status'],10752);self.assertEqual(r['worker_status'],0);self.assertTrue(r['collector_reaped']);self.assertEqual(r['final_mask'],r['original_mask']);self.assertFalse(r['root_remaining_new_FDs']);self.assertEqual([x['flags'] for x in r['clones']],[17,0]);self.assertTrue(r['clones'][0]['old_file_image_removed_before_first_child_instruction']);self.assertTrue(r['received']);self.assertTrue(all(x['plan_sha']==r['original_plan_sha'] for x in r['messages']));self.assertTrue(all(x['image_sha']==sha256(self.raw).hexdigest() for x in r['messages']));self.assertEqual([x['type'] for x in r['messages']],[3,4,1,2])
 def test_02_mutating_caller_input_after_clone_does_not_change_captured_plan(self):
  r=self.case('mutate-caller-plan',fault='mutate-input-after-clone');self.assertEqual(r['result'],11);self.assertTrue(all(x['plan_sha']==r['original_plan_sha'] for x in r['messages']))
 def test_03_bad_full_plan_or_image_binding_denies_before_allocation(self):
  original=M.plan(self.raw)
  for name,at,fixcrc in [('CRC',32,False),('image-SHA',112,True),('purpose',20,True),('reserved',200,True),('flags',160,True)]:
   p=bytearray(original);p[at]^=1
   if fixcrc:struct.pack_into('<I',p,252,zlib.crc32(p[:252]))
   r=self.case('bad-plan-'+name,job=bytes(p));self.assertEqual(r['result'],4);self.assertFalse(r['clones']);self.assertFalse(r['mapping_events'] if 'mapping_events' in r else r['mappings'])
  for name,issued,expires in [('expired',1,999),('future',2_000_000_000,3_000_000_000),('too-long',1_000_000_000,1_000_000_000_000)]:
   r=self.case(name,job=M.plan(self.raw,issued,expires));self.assertEqual(r['result'],4);self.assertFalse(r['clones'])
 def test_04_partial_preparation_failure_never_clones_or_leaks_mapping(self):
  for f in ['mmap-error','executable-protection-error','expire-after-copy','outer-clone-error','not-root']:
   r=self.case(f,fault=f);self.assertIn(r['result'],(2,4));self.assertFalse(r['clones']);self.assertEqual(r['final_mask'],r['original_mask']);self.assertFalse(r['root_remaining_new_FDs'])
 def test_05_worker_failure_or_wrong_HELLO_never_reports_success(self):
  for f in ['worker-close-error','worker-SIGKILL','bad-HELLO']:
   r=self.case(f,fault=f);self.assertEqual(r['result'],2);self.assertEqual(r['final_mask'],r['original_mask'])
 def test_06_early_or_absent_SIGCHLD_reaping_remains_unknown(self):
  for f in ['early-other-thread-reap','no-parent-reap','baseline-SIGCHLD-blocked']:
   r=self.case(f,fault=f);self.assertEqual(r['result'],2);self.assertEqual(r['final_mask'],r['original_mask'])
 def test_07_restore_failure_is_not_hidden_or_retried(self):
  r=self.case('mask-restore-error',fault='mask-restore-error');self.assertEqual(r['result'],2);self.assertNotEqual(r['final_mask'],r['original_mask'])
 def test_08_one_activation_per_loaded_capsule(self):
  k=M.Kernel(self.raw);g=M.Guest(k,k.root);g.run();self.assertEqual(k.root_result,11);clones=len(k.clone_events);k.root_result=None;g.u.reg_write(M.A.UC_ARM64_REG_PC,M.D.HEADER.unpack_from(self.raw)[4]+g.base-M.D.BASE);g.run();self.assertEqual(k.root_result,4);self.assertEqual(len(k.clone_events),clones);self.rows.append(dict(name='same-capsule-replay',summary=k.summary(g)))
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 out=dict(status='OWN_RUNTIME_PLAN_ANONYMOUS_CLONE_BRIDGE_SCOPED_PASS' if r.wasSuccessful() else 'FAIL',tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),details=[dict(test=str(t),traceback=tb) for t,tb in r.failures+r.errors],cases=Tests.rows,
  source_hashes={n:sha256((H/n).read_bytes()).hexdigest() for n in ['bridge.c','parent.c','collector.c','bridge_job.h','sha_impl.inc','bridge_build.py','model_bridge.py','test_bridge.py']},binary_sha256=sha256(Tests.raw).hexdigest(),
  only_own_ARM64_executed=True,actual_Linux_processes_or_threads_created=False,all_Linux_VFS_IPC_signal_clock_and_reaper_operations_are_explicit_fakes=True,
  original_Sony_Linux_glibc_or_driver_executed=False,new_device_operations=0,nonce_profile_and_controller_values_still_synthetic_not_authorization=True,
  global_cross_reload_owner_or_exclusive_endpoint_origin_proven=False,Sony_loader_constructor_and_current_target_verified=False,
  full_boot_worker_integrated=False,USB_or_full_job_resource_completion_verified=False,probe_deployable=False,first_flash_released=False)
 (RUN/'receipt.json').write_text(json.dumps(out,indent=2)+'\n');raise SystemExit(0 if r.wasSuccessful() else 1)
