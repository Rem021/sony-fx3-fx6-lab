from pathlib import Path
from hashlib import sha256
import json,struct,sys,unittest,zlib
import model_entry as M
D=M.D;H=Path(__file__).resolve().parent;RUN=Path(sys.argv[1]);sys.argv=sys.argv[:1]
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  RUN.mkdir(mode=0o700);cls.raw=(H/'build-initial/entry.so').read_bytes();cls.im=(H.parent/'stage218-fixed-shell-process-filter/originals/im.elf').read_bytes();cls.rows=[]
 def case(self,name,**kwargs):
  k,g,r=M.case(self.raw,self.im,**kwargs);self.rows.append(dict(name=name,summary=r));self.assertTrue(r['borrowed_FDs_unchanged']);self.assertFalse(r['source_accesses']);self.assertFalse(r['root_remaining_new_FDs']);self.assertFalse(r['root_remaining_anonymous']);return k,g,r
 def test_01_metadata_entry_and_full_preparation_to_bridge(self):
  meta=D.inspect_dynamic(self.raw);self.assertEqual(meta['DT_INIT'],json.loads((H/'build-initial/build.json').read_text())['global_offsets']['fx3_entry_init'])
  for pid,tid,base,clock in [(321,777,0x30000000,1_000_000_000),(9011,9022,0x20000000,100_000_000_000),(90,91,0x60000000,900_000_000_000)]:
   k,g,r=self.case('normal-'+str(pid),pid=pid,tid=tid,base=base,clock=clock)
   self.assertEqual(r['result'],11);self.assertEqual(r['collector_status'],10752);self.assertEqual(r['worker_status'],0);self.assertEqual(r['original_mask'],r['final_mask']);self.assertTrue(r['collector_reaped']);self.assertTrue(r['clones'][0]['old_file_image_removed_before_first_child_instruction'])
   self.assertNotEqual(r['full_file_sha256'],r['immutable_image_id']);p=k.original_published_plan;self.assertEqual(p[112:144].hex(),r['immutable_image_id']);self.assertEqual(struct.unpack_from('<I',p,252)[0],zlib.crc32(p[:252]));self.assertEqual(r['files'][M.PLAN]['mode']&0o7777,0o600)
   record=bytes(k.fs.nodes[M.STAGED].data);self.assertEqual(record[48:80].hex(),r['full_file_sha256']);self.assertEqual(record[112:144].hex(),r['immutable_image_id']);self.assertEqual(record[80:112].hex(),sha256(p).hexdigest());self.assertTrue(all(x['plan_sha']==sha256(p).hexdigest() and x['image_sha']==r['immutable_image_id'] for x in r['messages']))
 def test_02_direct_DT_INIT_target_ignores_external_plan_arguments(self):
  k=M.Kernel(self.raw,self.im);g=M.Guest(k,k.root);entry=D.HEADER.unpack_from(self.raw)[4]
  g.u.reg_write(M.A.UC_ARM64_REG_PC,g.base+D.inspect_dynamic(self.raw)['DT_INIT']);g.u.reg_write(M.A.UC_ARM64_REG_LR,g.base+entry+4)
  for i,value in enumerate([0xdeadbeef,0xffffffffffffffff,0x12345]):g.u.reg_write(M.REG[i] if hasattr(M,'REG') else M.M.REG[i],value)
  g.run();r=k.summary(g);self.rows.append(dict(name='direct-DT_INIT-target',summary=r));self.assertEqual(r['result'],11)
 def test_03_preparation_failures_never_start_bridge(self):
  for fault in ['wrong-parent','image-file','unsafe-root','non-RAM','claim-mode','restrictive-mode','existing-plan','short-plan-write','report-write','plan-fsync','plan-readback','pending-close','rename-unsupported','publish-race','post-publish-corrupt','post-publish-inode','expire-after-publish','post-publish-root-close','expire-during-final-close','clock-invalid','expired-before-publish']:
   k,g,r=self.case(fault,prepare_fault=fault);self.assertIn(r['result'],[2,4]);self.assertFalse(r['clones']);self.assertFalse(r['mappings']);self.assertEqual(r['original_mask'],r['final_mask'])
   if fault=='existing-plan':self.assertEqual(bytes(k.fs.nodes[M.PLAN].data),b'preexisting plan')
   if fault=='publish-race':self.assertEqual(bytes(k.fs.nodes[M.PLAN].data),b'racing plan')
 def test_04_success_or_failure_claims_block_fresh_loads(self):
  for fault in [None,'short-plan-write','post-publish-root-close']:
   k,g,r=self.case('first-'+str(fault),prepare_fault=fault);before={n:bytes(x.data) for n,x in k.fs.nodes.items() if n.startswith(M.CLAIM) or n==M.PLAN}
   k2,g2,r2=self.case('fresh-after-'+str(fault),fs=k.fs,pid=901,tid=909);self.assertEqual(r2['result'],2);self.assertFalse(r2['clones']);self.assertEqual(before,{n:bytes(x.data) for n,x in k.fs.nodes.items() if n.startswith(M.CLAIM) or n==M.PLAN})
 def test_05_interleaved_second_load_and_different_nonce_cannot_overlap(self):
  for changed in [False,True]:
   k=M.Kernel(self.raw,self.im);raw2=bytearray(self.raw)
   if changed:raw2[4096+32]^=1;struct.pack_into('<I',raw2,4096+252,zlib.crc32(raw2[4096:4096+252]))
   def other():
    k.fs.nodes[M.IMAGE].data[:]=raw2;k2,g2,r2=M.case(bytes(raw2),self.im,fs=k.fs,pid=800,tid=801);self.assertEqual(r2['result'],2);self.assertFalse(r2['clones']);k.other_results.append(r2)
   k.after_claim=other;g=M.Guest(k,k.root);g.run();r=k.summary(g);self.rows.append(dict(name='interleaved-nonce-'+str(changed),summary=r));self.assertEqual(r['result'],11);self.assertEqual([x['result'] for x in r['claims']],[0,-17])
 def test_06_changed_published_file_does_not_replace_captured_plan(self):
  k,g,r=self.case('mutate-after-prepare',prepare_fault='mutate-published-after-prepare');self.assertEqual(r['result'],11);self.assertNotEqual(bytes(k.fs.nodes[M.PLAN].data),k.original_published_plan);self.assertTrue(all(x['plan_sha']==sha256(k.original_published_plan).hexdigest() for x in r['messages']))
 def test_07_bridge_failure_retains_global_claim(self):
  for fault in ['outer-clone-error','worker-close-error','early-other-thread-reap','no-parent-reap','mask-restore-error']:
   k,g,r=self.case('bridge-'+fault,fault=fault);self.assertEqual(r['result'],2);self.assertIn(M.CLAIM,k.fs.nodes)
 def test_08_bad_configuration_denies_without_claim(self):
  for offset in [4096,4096+20,4096+32,4096+160]:
   data=bytearray(self.raw);data[offset]^=1;k,g,r=M.case(bytes(data),self.im);self.rows.append(dict(name='bad-config-'+str(offset),summary=r));self.assertEqual(r['result'],4);self.assertFalse(r['claims']);self.assertFalse(r['clones'])
 def test_09_mutable_file_padding_is_not_authenticated_by_image_ID(self):
  k,g,r=self.case('mutable-padding-boundary',prepare_fault='mutable-file-padding');self.assertEqual(r['result'],11)
  self.assertNotEqual(r['full_file_sha256'],r['observed_image_file_sha256']);record=bytes(k.fs.nodes[M.STAGED].data)
  self.assertEqual(record[48:80].hex(),r['observed_image_file_sha256']);self.assertEqual(record[112:144].hex(),r['immutable_image_id'])
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 names=['front.c','bridge.c','parent.c','collector.c','bridge_job.h','core_support.inc','parent_ipc.inc','sha_impl.inc','entry_build.py','model_entry.py','test_entry.py']
 snap=RUN/'source-snapshot';snap.mkdir(mode=0o700)
 for n in names:(snap/n).open('xb').write((H/n).read_bytes())
 out=dict(status='OWN_DT_INIT_PREPARATION_AND_CROSS_LOAD_CLAIM_SCOPED_PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),details=[dict(test=str(t),traceback=tb) for t,tb in result.failures+result.errors],cases=Tests.rows,source_hashes={n:sha256((H/n).read_bytes()).hexdigest() for n in names},binary_sha256=sha256(Tests.raw).hexdigest(),immutable_image_id=sha256(Tests.raw[:3*D.PAGE]+bytes(D.PAGE)).hexdigest(),original_im_sha256=sha256(Tests.im).hexdigest(),only_own_ARM64_executed=True,original_im_file_hashed_but_no_original_Sony_Linux_glibc_or_downloaded_code_executed=True,all_Linux_VFS_IPC_process_signal_time_and_loader_entry_are_explicit_models=True,shared_VFS_mkdir_interleavings_not_actual_Linux_concurrency=True,new_device_operations=0,actual_Sony_dlopen_controller_authorization_namespace_and_host_return_verified=False,full_boot_reader_integrated=False,independent_AP_restore_or_MAIN_HEVC_verified=False,probe_deployable=False,first_flash_released=False)
 (RUN/'receipt.json').open('x').write(json.dumps(out,indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful() else 1)
