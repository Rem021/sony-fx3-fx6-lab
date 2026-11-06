from launch_model import *
import unittest
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  check_volume();RUN.mkdir(mode=0o700);cls.build=D.build(RUN/'built');cls.raw=read_file(RUN/'built/parent-module.so',4*1024*1024)
  cls.image=read_file(H.parent/'stage223-static-worker-and-scoped-job-descriptors/runs-import-fixed/built/worker.elf',4*1024*1024)
  assert sha256(cls.image).hexdigest()=='e40d068d43123f8f86eba5c46a1428e02e5e16c84df2211174c578d4cd273d7d'
  cls.source=H.parent/'stage219-bound-handoff-and-request-claims/runs-final-v2/fixture/synthetic.boot';cls.profiles={}
  for path,size,digest in B.FILE_PROFILE:
   data=read_file(R/'work/sony-firmware-20261024/stage213-AP-eMMC-boot-asset-search/originals/current-p3-initrd'/path.lstrip('/'),size);assert sha256(data).hexdigest()==digest;cls.profiles[path]=data
  cls.im=read_file(H.parent/'stage218-fixed-shell-process-filter/originals/im.elf',40920);cls.cases=[];cls.instances=[];cls.pid=4321
 def pair(self,name,fault=None,req=None,parent=None,total=B.UNIT,shared=None,nonce='c'*64,namespace=None,ram=None):
  req=req or B.request('b'*32,'boot0',0);l=M.Link(req,321,self.pid,nonce);type(self).pid+=1
  hand=bytearray(N.M.W.packet(req,2,321,1_000_000_000,'d'*64,nonce));struct.pack_into('<I',hand,128,0);struct.pack_into('<I',hand,252,zlib.crc32(hand[:252]))
  if parent is None:
   image=self.image
   if fault=='image-byte':image=image[:65540]+bytes([image[65540]^1])+image[65541:]
   k=ParentKernel(name,self.source,self.profiles,self.im,namespace or RUN/(name+'-owner'),l,image,ram,shared,fault,total);g=ParentGuest(self.raw,k);g.init();self.assertEqual(g.trace,[])
  else:k,g=parent;k.prepare(l);k.launch_fault=fault
  q=dict(name=name,k=k,g=g,l=l,hand=bytes(hand),req=req);self.instances.append(q);return q
 def launch(self,q):return q['g'].launch(q['hand'],q['req'])
 def drive(self,q):
  until=time.monotonic()+25
  while time.monotonic()<until:
   state=q['g'].poll()
   if state in (0,2):return state
   time.sleep(.005)
  self.fail('own launch chain observation timeout')
 def finish(self,q,state):
  k,g,l=q['k'],q['g'],q['l']
  if l.thread is not None:l.thread.join(timeout=12)
  if l.thread is not None and l.thread.is_alive():l.release_fixture();l.thread.join(timeout=12)
  self.assertTrue(l.thread is None or not l.thread.is_alive());self.assertEqual(l.errors,[]);self.assertEqual(g.errors,[]);self.assertEqual(k.errors,[])
  child=l.child;guest=l.guest
  if child is not None:
   self.assertEqual(child.errors,[]);self.assertEqual(guest.errors,[])
   for fd,flags in k.parent_flags_before.items():self.assertEqual(k.fds[fd].get('flags',1),flags)
  self.cases.append(dict(name=q['name'],state=state,events=k.events.copy(),clones=k.clones.copy(),execs=k.execs.copy(),stages=k.stages.copy(),parent_packets=l.parent_packets,child_packets=l.child_packets,child_exit=l.child_return,source_reads=len(child.source_reads) if child else 0,exec_closed=child.exec_closed if child else [],role_FDs=[child.image_fd,child.job_fd,child.socket_fd] if child else [],parent_flags_unchanged=True,reaped=l.reaped,child_errors=guest.errors if guest else [],parent_errors=g.errors.copy()))
 @classmethod
 def tearDownClass(cls):
  for q in cls.instances:
   l=q['l']
   if l.thread is not None and l.thread.is_alive():l.release_fixture();l.thread.join(timeout=12)
   # Normal local fixture shutdown only; retained parent FDs are not a target release.
   k=q['k']
   for fd,row in k.fds.items():
    if row['real'] is not None and fd not in k.closed:os.close(row['real']);k.closed.append(fd)
 def test_01_launches_own_clone_child_exec_static_start_and_parent_completion(self):
  q=self.pair('normal');self.assertEqual(self.launch(q),1,q['g'].errors);state=self.drive(q);self.assertEqual(state,0,q['l'].errors);self.finish(q,state)
  k,l=q['k'],q['l'];self.assertEqual(l.child_return,0);self.assertEqual(l.parent_packets,[1,3]);self.assertEqual(l.child_packets,[2,4]);self.assertEqual(len(l.child.source_reads),2)
  self.assertLess(k.events.index('reserve-session'),k.events.index('open-image'));self.assertLess(k.events.index('clone'),k.events.index('pwrite:fx3-boot-handoff-v1.bin'))
  self.assertTrue(set([0,1,2,900]).issubset(l.child.exec_closed));self.assertNotIn(900,[l.child.image_fd,l.child.job_fd,l.child.socket_fd])
 def test_02_image_mismatch_flags_owner_and_metadata_stop_before_clone(self):
  for fault in ['image-byte','image-writable','image-owner','image-drift']:
   q=self.pair(fault,fault);self.assertEqual(self.launch(q),2,q['g'].errors);self.assertEqual(q['k'].clones,[]);self.assertEqual(q['k'].stages,[]);self.finish(q,2)
 def test_03_clone_and_socket_creation_failure_are_not_success(self):
  for fault in ['socketpair','clone']:
   q=self.pair(fault,fault);self.assertEqual(self.launch(q),2,q['g'].errors);self.finish(q,2);self.assertEqual(q['l'].parent_packets,[])
 def test_04_child_whitelist_enumeration_or_exec_failure_reaches_exit(self):
  for fault,code in [('child-flags',90),('bad-dirent',90),('exec',93)]:
   q=self.pair(fault,fault);self.assertIn(self.launch(q),(1,2),q['g'].errors);state=self.drive(q);self.assertEqual(state,2);self.finish(q,state);self.assertEqual(q['l'].child_return,code);self.assertEqual(q['l'].child.source_reads,[])
 def test_05_partial_staging_cannot_send_grant(self):
  for fault in ['stage-short','stage-sync']:
   q=self.pair(fault,fault);self.assertEqual(self.launch(q),2,q['g'].errors)
   # Wake the same self-written model child so absence of GRANT reaches timeout.
   q['l'].release_fixture();q['l'].thread.join(timeout=12);self.drive(q);self.finish(q,2);self.assertEqual(q['l'].parent_packets,[]);self.assertEqual(q['l'].child.source_reads,[])
 def test_06_existing_inputs_are_not_overwritten_and_old_owner_blocks(self):
  ram=RUN/'existing-ram';ram.mkdir(mode=0o700);old=b'old-input';(ram/'fx3-boot-handoff-v1.bin').write_bytes(old)
  q=self.pair('existing',ram=ram);self.assertEqual(self.launch(q),2,q['g'].errors);self.finish(q,2);self.assertEqual((ram/'fx3-boot-handoff-v1.bin').read_bytes(),old)
  q2=self.pair('second-owner',namespace=q['k'].namespace,ram=ram);self.assertEqual(self.launch(q2),2,q2['g'].errors);self.finish(q2,2);self.assertEqual(q2['k'].events,['reserve-session'])
 def test_07_full_four_windows_reuse_only_same_live_input_descriptors(self):
  parent=None;outputs=[];shared=RUN/'full-claims'
  for i in range(4):
   req=B.request('e'*32,'boot1',i,0 if i==0 else B.MAX_BOOT);q=self.pair('full-'+str(i),req=req,parent=parent,total=B.MAX_BOOT,shared=shared,nonce=str(i+1)*64)
   self.assertEqual(self.launch(q),1,q['g'].errors);state=self.drive(q);self.assertEqual(state,0,q['l'].errors);self.finish(q,state);outputs.append(q['l'].child.output);parent=(q['k'],q['g'])
  report=B.assemble_windows(outputs,[0]*4,RUN/'assembled','1'*64);self.assertEqual(report['sha256'],sha256(self.source.read_bytes()).hexdigest())
  self.assertEqual(sum(x.startswith('create-input:') for x in parent[0].events),2)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 d=dict(schema='fx3-controlled-launcher-own-ARM64-fake-Linux-v1',status='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),details=[dict(test=str(t),traceback=tb) for t,tb in result.failures+result.errors],cases=Tests.cases,build=Tests.build,all_model_threads_terminal=all(q['l'].thread is None or not q['l'].thread.is_alive() for q in Tests.instances),source_hashes={p.name:sha256(p.read_bytes()).hexdigest() for p in [H/'parent_module.c',H/'launch_support.inc',H/'dynparent.py',H/'launch_model.py',H/'test_launcher.py']},own_clone_branches_and_exec_transition_modeled=True,actual_Linux_clone_exec_FD_credentials_or_kernel_ELF_acceptance_verified=False,Sony_BusyBox_glibc_or_Linux_kernel_executed=False,new_camera_operations=0,hardware_validated=False,independent_recovery_proven=False,flashable=False)
 new_directory(RUN/'receipt',{'results.json':encode(d)});raise SystemExit(0 if result.wasSuccessful() else 1)
