from pathlib import Path
from hashlib import sha256
import json,struct,sys,unittest,zlib
import model_result as M
import result_protocol as P
H=Path(__file__).resolve().parent;RUN=Path(sys.argv[1]);sys.argv=sys.argv[:1]
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  RUN.mkdir(mode=0o700);cls.raw=(H/'build-initial/entry.so').read_bytes();cls.im=(H.parent/'stage218-fixed-shell-process-filter/originals/im.elf').read_bytes();cls.rows=[];cls.expect=P.Expected.from_artifact(cls.raw,pinned_file_sha=sha256(cls.raw).digest(),nonce=b'\xbb'*16,profile=b'\xcc'*32,controller=b'\xdd'*32)
 def case(self,name,**kwargs):
  k,g,r=M.case(self.raw,self.im,**kwargs);self.rows.append(dict(name=name,summary=r));self.assertTrue(r['borrowed_FDs_unchanged']);self.assertFalse(r['source_accesses']);self.assertFalse(r['root_remaining_new_FDs']);self.assertFalse(r['root_remaining_anonymous']);return k,g,r
 def body(self,r):return bytes(4)+bytes.fromhex(r['result_record_hex'])
 def test_01_actual_own_C_record_decodes_against_external_artifact_pin(self):
  for pid,tid,clock in [(321,777,1_000_000_000),(9011,9022,100_000_000_000)]:
   k,g,r=self.case('normal-'+str(pid),pid=pid,tid=tid,clock=clock);self.assertEqual(r['result'],11);record=bytes(k.fs.nodes[M.RESULT].data);self.assertEqual(len(record),256);out=P.decode_native_body(self.body(r),self.expect);self.assertEqual(out['reported_core_status'],11);self.assertEqual((out['pid'],out['tid']),(pid,tid));self.assertFalse(out['may_release_owner_or_flash']);self.assertFalse(out['report_close_setter_return_USB_or_full_job_completion_proven']);self.assertEqual(record[112:144],sha256(k.original_published_plan).digest())
  self.good_body=self.body(r)
 def test_02_late_publication_errors_cannot_become_global_completion(self):
  for fault in ['fsync','readback','close','owner-close','root-close','expire-after-close']:
   k,g,r=self.case('result-'+fault,result_fault=fault);self.assertEqual(r['result'],2);out=P.decode_native_body(self.body(r),self.expect);self.assertEqual(out['reported_core_status'],11);self.assertEqual(out['record_phase'],'BEFORE_REPORT_PUBLICATION_CLEANUP');self.assertFalse(out['may_release_owner_or_flash'])
 def test_03_missing_partial_or_preexisting_records_are_not_accepted(self):
  for fault in ['open','short-write','existing']:
   k,g,r=self.case('result-'+fault,result_fault=fault);self.assertEqual(r['result'],2)
   body=self.body(r) if r['result_record_hex'] is not None else bytes(4)
   with self.assertRaises(ValueError):P.decode_native_body(body,self.expect)
   if fault=='existing':self.assertEqual(bytes(k.fs.nodes[M.RESULT].data),b'older unrelated record')
 def test_04_HELD_core_report_is_not_success(self):
  for fault in ['worker-close-error','mask-restore-error','no-parent-reap']:
   k,g,r=self.case('core-'+fault,fault=fault);self.assertEqual(r['result'],2);out=P.decode_native_body(self.body(r),self.expect);self.assertEqual(out['reported_core_status'],2);self.assertFalse(out['may_release_owner_or_flash'])
 def test_05_mutable_file_change_is_rejected_by_pinned_full_SHA(self):
  k,g,r=self.case('changed-file-RW-padding',prepare_fault='mutable-file-padding');self.assertEqual(r['result'],11)
  with self.assertRaises(ValueError):P.decode_native_body(self.body(r),self.expect)
 def test_06_strict_identity_plan_time_phase_and_native_body(self):
  k,g,r=self.case('codec-fixture');body=self.body(r);p=body[4:];rejects=[]
  for name,offset in [('magic',0),('version',16),('purpose',20),('status',24),('reason',28),('nonce',32),('file',48),('image',80),('plan',112),('profile',144),('controller',176),('issued',208),('expiry',216),('reserved',244)]:
   wrong=bytearray(p);wrong[offset]^=1;struct.pack_into('<I',wrong,252,zlib.crc32(wrong[:252]))
   with self.assertRaises(ValueError,msg=name):P.decode_native_body(bytes(4)+bytes(wrong),self.expect)
   rejects.append(name)
  for name,offset,value,fmt in [('late-finish',224,struct.unpack_from('<Q',p,216)[0],'<Q'),('PID',232,0,'<I'),('TID',236,1,'<I'),('phase',240,2,'<I')]:
   wrong=bytearray(p);struct.pack_into(fmt,wrong,offset,value);struct.pack_into('<I',wrong,252,zlib.crc32(wrong[:252]))
   with self.assertRaises(ValueError,msg=name):P.decode_native_body(bytes(4)+bytes(wrong),self.expect)
   rejects.append(name)
  for wrong in [body[:-1],body+b'\0',struct.pack('<I',0x10000006)+p,b'\0'*260,body[:-1]+bytes([body[-1]^1])]:
   with self.assertRaises(ValueError):P.decode_native_body(wrong,self.expect)
  self.rows.append(dict(name='codec-rejections',rejected_fields=rejects,native_error_short_extra_CRC_and_zero_bodies_rejected=True))
 def test_07_artifact_pin_and_associations_are_external_required_inputs(self):
  for key,size in [('pinned_file_sha',32),('nonce',16),('profile',32),('controller',32)]:
   args=dict(pinned_file_sha=sha256(self.raw).digest(),nonce=b'\xbb'*16,profile=b'\xcc'*32,controller=b'\xdd'*32);args[key]=b'\xee'*size
   with self.assertRaises(ValueError,msg=key):P.Expected.from_artifact(self.raw,**args)
  self.rows.append(dict(name='external-pin-rejections',fields=['file_SHA','nonce','profile','controller']))
 def test_08_only_fixed_RAM_candidate_frames_no_generic_path_or_transport(self):
  a,b=P.candidate_read_frames(self.expect);self.assertEqual(a,bytes.fromhex('01100f0000')+P.SELECTED_RESULT.encode()+b'\0');self.assertEqual(b,bytes.fromhex('0110110000ff00'));self.assertEqual(P.SELECTED_RESULT,'/tmp/jiritsu/../..'+P.RAM_RESULT);self.assertLess(len(a)-4,513)
  with self.assertRaises(ValueError):P.candidate_read_frames(None)
  self.rows.append(dict(name='fixed-read-envelope',select_hex=a.hex(),read_hex=b.hex(),actual_dispatch=False))
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));names=['front.c','bridge.c','parent.c','collector.c','bridge_job.h','core_support.inc','parent_ipc.inc','sha_impl.inc','entry_build.py','model_result.py','result_protocol.py','test_result.py'];snap=RUN/'source-snapshot';snap.mkdir(mode=0o700)
 for n in names:(snap/n).open('xb').write((H/n).read_bytes())
 out=dict(status='OWN_C_LOCAL_RECORD_AND_PINNED_HOST_DECODER_SCOPED_PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),details=[dict(test=str(t),traceback=tb) for t,tb in result.failures+result.errors],cases=Tests.rows,source_hashes={n:sha256((H/n).read_bytes()).hexdigest() for n in names},binary_sha256=sha256(Tests.raw).hexdigest(),only_own_ARM64_and_own_host_python_executed=True,native_Sony_GET_Senser_glibc_Linux_or_USB_not_executed=True,native_reply_body_in_tests_is_model_serialization=True,observed_local_record_never_authorizes_flash_or_global_completion=True,current_camera_identity_authenticated_channel_and_exclusive_selected_path_verified=False,new_device_operations=0,full_boot_backup_independent_AP_restore_or_MAIN_HEVC_verified=False,probe_deployable=False,first_flash_released=False)
 (RUN/'receipt.json').open('x').write(json.dumps(out,indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful() else 1)
