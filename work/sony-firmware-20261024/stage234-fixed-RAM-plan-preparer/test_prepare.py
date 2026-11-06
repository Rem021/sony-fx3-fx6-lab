from model_prepare import *
import unittest
RUN=Path(sys.argv[1]);sys.argv=sys.argv[:1]
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  RUN.mkdir(mode=0o700);cls.build=D.build(RUN/'built');cls.raw=(RUN/'built/parent-module.so').read_bytes();cls.im=(B/'stage218-fixed-shell-process-filter/originals/im.elf').read_bytes();cls.rows=[];cls.objects=[]
 def run_case(self,name,fault=None):
  k=Kernel(self.raw,self.im,fault);g=Guest(self.raw,k.parent);self.objects.append((name,k,g))
  if fault=='bad-loaded-config':g.u.mem_write(g.base+D.CONFIG_AT+252,b'\x00\x00\x00\x00')
  if fault=='bad-loaded-RO':g.u.mem_write(g.base+0x1700,b'\xaa')
  result=g.initialize();g.unload();self.assertFalse(k.forbidden);self.assertFalse(k.clone_events);self.assertFalse(k.signal_ops);self.assertEqual(k.parent.mask,0x400);self.assertFalse(k.source_accesses);self.assertFalse(k.exec_attempts);return k,g,result
 def record(self,name,k,result):self.rows.append(dict(name=name,result=list(result),summary=k.prepare_summary()))
 def test_01_normal_full_plan_matches_fixed_worker_schema_and_replay_refuses(self):
  k,g,result=self.run_case('normal');self.assertEqual(result,(1,0));plan=bytes(k.nodes[PLAN].data);self.assertEqual(plan[:16],b'FX3ENTRYPLANv1'.ljust(16,b'\0'));self.assertEqual(struct.unpack_from('<III',plan,16),(1,1,1));self.assertEqual(plan[112:144].hex(),D.WORKER_SHA);self.assertEqual(struct.unpack_from('<I',plan,252)[0],zlib.crc32(plan[:252]));self.assertEqual(k.nodes[PLAN].mode&0o7777,0o600);self.assertNotIn(PENDING,k.nodes);self.assertEqual(k.prepare_summary()['remaining_new_FDs'],[])
  report=bytes(k.nodes[REPORT].data);self.assertEqual(report[:16],b'FX3PREPSTAGED1'.ljust(16,b'\0'));self.assertEqual(report[48:80],sha256(self.raw).digest());self.assertEqual(report[80:112],sha256(plan).digest());self.assertEqual(struct.unpack_from('<QQ',report,200),(k.nodes[PLAN].dev,k.nodes[PLAN].ino));self.record('normal',k,result)
  previous=bytes(k.nodes[PLAN].data);again=Guest(self.raw,k.parent);self.assertEqual(again.initialize(),(2,11));again.unload();self.assertEqual(bytes(k.nodes[PLAN].data),previous);self.record('replay',k,(2,11))
 def test_02_bad_profiles_or_loaded_config_never_claim(self):
  for fault in ['wrong-parent','image-file','bad-loaded-config','bad-loaded-RO']:
   k,g,result=self.run_case(fault,fault);self.assertEqual(result,(4,0));self.assertNotIn(CLAIM,k.nodes);self.assertNotIn(PLAN,k.nodes);self.record(fault,k,result)
 def test_03_RAM_directory_and_mode_checks_prevent_publication(self):
  for fault,reason in [('non-RAM',10),('unsafe-root',10),('claim-mode',12),('restrictive-mode',14)]:
   k,g,result=self.run_case(fault,fault);self.assertEqual(result,(2,reason));self.assertNotIn(PLAN,k.nodes);self.assertFalse(k.publications);self.record(fault,k,result)
 def test_04_clock_or_partial_staging_failure_never_publishes(self):
  for fault,reason in [('clock-invalid',13),('expired-before-publish',16),('clock-backwards',16),('short-plan-write',14),('plan-fsync',14),('plan-readback',14),('report-write',15),('pending-close',14)]:
   k,g,result=self.run_case(fault,fault);self.assertEqual(result,(2,reason));self.assertNotIn(PLAN,k.nodes);self.assertFalse(k.publications);self.record(fault,k,result)
 def test_05_no_replace_rejects_existing_racing_and_unsupported(self):
  for fault in ['existing-plan','publish-race','rename-unsupported']:
   k,g,result=self.run_case(fault,fault);self.assertEqual(result,(2,17));self.assertEqual(len(k.publications),1);self.assertFalse(k.publications[0]['published']);self.assertIn(PENDING,k.nodes)
   if fault!='rename-unsupported':self.assertIn(b'must remain',bytes(k.nodes[PLAN].data))
   else:self.assertNotIn(PLAN,k.nodes)
   self.record(fault,k,result)
 def test_06_error_after_publish_keeps_plan_but_never_reports_ready(self):
  for fault,reason in [('post-publish-corrupt',18),('post-publish-inode',18),('post-publish-root-close',20),('expire-after-publish',21),('expire-during-final-close',21)]:
   k,g,result=self.run_case(fault,fault);self.assertEqual(result,(2,reason));self.assertTrue(k.publications[-1]['published']);self.assertIn(PLAN,k.nodes);self.assertIn(REPORT,k.nodes);self.record(fault,k,result)
 def test_07_generated_plan_is_accepted_by_existing_own_worker_START(self):
  k,g,result=self.run_case('worker-start-handoff');self.assertEqual(result,(1,0));worker=(B/'stage231-constructor-noexec-child-and-reload-observer/runs-bounded-verified/built/parent-module.so').read_bytes();self.assertEqual(sha256(worker).hexdigest(),D.WORKER_SHA)
  k.allow_worker=True;k.raw=worker;k.nodes['/tmp/jiritsu/libJit.so'].data[:]=worker;k.nodes['/tmp/jiritsu/libJit.so'].gen+=1;entry=M.Guest(worker,k.parent);self.assertEqual(entry.initialize(),(1,0));entry.unload();k.child.guest.drop_original_file_backing();self.assertEqual(k.child.guest.run_child(),0);self.assertFalse(k.source_accesses);self.record('worker-start-handoff',k,result)
  # START only: no synthetic external mutation of the generated plan to claim
  # an implemented START-to-OBSERVE transition or complete backup lifecycle.
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 out=dict(schema='fx3-fixed-RAM-plan-preparer-own-ARM64-model-v1',status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),details=[dict(test=str(t),traceback=tb) for t,tb in result.failures+result.errors],build=getattr(Tests,'build',None),cases=Tests.rows,debug=[dict(name=n,errors=g.errors,trace=g.trace[-15:]) for n,k,g in Tests.objects],source_hashes={n:sha256((H/n).read_bytes()).hexdigest() for n in ['prepare.c','prepare_build.py','core_support.inc','parent_ipc.inc','model_prepare.py','test_prepare.py']},only_own_ARM64_executed=True,actual_Linux_processes_or_threads_created=False,original_Sony_Linux_or_glibc_executed=False,new_device_operations=0,boot_device_card_or_recording_source_reads=0,actual_tmpfs_renameat2_loader_body_or_host_transport_verified=False,synthetic_association_fields_only=True,START_to_OBSERVE_transition_implemented=False,full_boot_worker_integrated=False,first_flash_released=False,goal_complete=False)
 (RUN/'receipt.json').write_text(json.dumps(out,indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful() else 1)
