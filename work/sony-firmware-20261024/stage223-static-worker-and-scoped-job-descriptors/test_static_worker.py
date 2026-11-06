"""Own standalone _start/exit93 plus unchanged 222 parent; no actual exec."""
from pathlib import Path
from hashlib import sha256
import json,sys,time,unittest
from static_model import H,R,RUN,M,N,S,P,B,Kernel,Guest,read_file,new_directory,encode,check_volume

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_volume();RUN.mkdir(mode=0o700);cls.build=S.build(RUN/'built');cls.raw=read_file(RUN/'built/worker.elf',S.MAX_OBJECT)
        cls.parent_raw=read_file(H.parent/'stage222-parent-arbiter-core-and-paired-ARM64/runs-final/built/parent-module.so',S.MAX_OBJECT)
        assert sha256(cls.parent_raw).hexdigest()=='5a9ab04e92e06dd5fbddbff0c95e1736ac4c0850a8ad9a346a01669104e0eb39'
        cls.source=H.parent/'stage219-bound-handoff-and-request-claims/runs-final-v2/fixture/synthetic.boot';cls.profiles={}
        for path,size,digest in B.FILE_PROFILE:
            data=read_file(R/'work/sony-firmware-20261024/stage213-AP-eMMC-boot-asset-search/originals/current-p3-initrd'/path.lstrip('/'),size)
            assert sha256(data).hexdigest()==digest;cls.profiles[path]=data
        cls.im=read_file(H.parent/'stage218-fixed-shell-process-filter/originals/im.elf',40920)
        cls.pairs=[];cls.cases=[];cls.pid=1234

    def pair(self,name,req=None,total=B.UNIT,parent=None,shared=None,nonce='c'*64,fault=None,mode=None,roles=(71,72,73)):
        req=req or B.request('b'*32,'boot0',0);link=M.Link(req,321,self.pid,nonce,mode);type(self).pid+=1
        k=Kernel(name+'-child',self.source,self.profiles,self.im,shared or RUN/(name+'-claims'),link,self.raw,total,fault,roles)
        g=Guest(self.raw,k);self.assertEqual(g.trace,[])
        if parent is None:
            pk=M.ParentKernel(name+'-parent',self.source,self.profiles,self.im,RUN/(name+'-global'),link)
            pg=M.ParentGuest(self.parent_raw,pk);pg.init();self.assertEqual(pg.trace,[])
        else:pk,pg=parent;pk.prepare(link)
        q=dict(name=name,link=link,k=k,g=g,pk=pk,pg=pg);self.pairs.append(q);return q

    def start(self,q):
        self.assertEqual(q['pg'].submit(q['k'].hand,q['link'].request,q['link'].child_pid),1)
        q['link'].start_child(q['k'],q['g'])

    def drive(self,q,predicate=None):
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            state=q['pg'].poll()
            if predicate is not None and predicate(state):return state
            if predicate is None and state in (0,2):return state
            time.sleep(.005)
        raise AssertionError('same live static child observation timeout')

    def finish(self,q,state):
        l=q['link']
        if l.thread.is_alive():l.release_fixture();l.thread.join(timeout=12)
        self.assertFalse(l.thread.is_alive());self.assertEqual(l.errors,[])
        for _ in range(3):q['pg'].poll()
        self.assertEqual(q['g'].errors,[]);self.assertEqual(q['k'].errors,[]);self.assertEqual(q['pg'].errors,[]);self.assertEqual(q['pk'].errors,[])
        self.assertEqual(set(q['k'].fds),set(q['k'].closed))
        self.cases.append(dict(name=q['name'],state=state,child_exit=q['g'].exitcode,source_reads=len(q['k'].source_reads),parent_packets=l.parent_packets,child_packets=l.child_packets,
            entry=q['g'].entry,first_syscall=q['g'].trace[0]['number'] if q['g'].trace else None,last_syscall=q['g'].trace[-1]['number'],
            inherited_roles=[q['k'].image_fd,q['k'].job_fd,q['k'].socket_fd],kernel_exit_cleanup=q['k'].exit_closed,
            explicit_role_closes=[fd for fd in (q['k'].image_fd,q['k'].job_fd,q['k'].socket_fd) if fd in q['k'].closed and fd not in q['k'].exit_closed],
            fcntl_checks=q['k'].fcntl_calls,syscalls=len(q['g'].trace),reaped=l.reaped))

    def test_01_static_start_to_exit_and_parent_reread(self):
        q=self.pair('normal');self.start(q);state=self.drive(q);self.assertEqual(state,0);self.finish(q,state)
        self.assertEqual(q['g'].exitcode,0);self.assertEqual(q['link'].parent_packets,[1,3]);self.assertEqual(q['link'].child_packets,[2,4])
        data,info=B.decode_window(q['k'].output,0);self.assertEqual(data,self.source.read_bytes()[:B.UNIT])
        self.assertEqual(q['k'].exit_closed,[])

    def test_02_descriptor_numbers_are_not_fixed_or_stdio_dependent(self):
        for i,roles in enumerate(((0,1,2),(181,182,183))):
            q=self.pair('roles-'+str(i),roles=roles);self.start(q);state=self.drive(q);self.assertEqual(state,0);self.finish(q,state)

    def test_03_argv_and_missing_descriptor_fail_before_private_source(self):
        for fault in ('argv-leading-zero','argv-negative','argv-overflow','argv-duplicate','argv-extra','argv-missing-nul','argv-fd-missing'):
            q=self.pair(fault,fault=fault);self.start(q);state=self.drive(q);self.assertEqual(state,2);self.finish(q,state);self.assertEqual(q['k'].source_reads,[])

    def test_04_image_flags_inode_uid_and_root_anchor_are_strict(self):
        for fault in ('image-mismatch','image-uid','image-mode','image-writable','cloexec','wrong-directory'):
            q=self.pair(fault,fault=fault);self.start(q);state=self.drive(q);self.assertEqual(state,2);self.finish(q,state);self.assertEqual(q['k'].source_reads,[])

    def test_05_full_four_windows_keep_global_replay_namespace(self):
        parent=None;outputs=[];shared=RUN/'full-claims'
        for window in range(4):
            req=B.request('b'*32,'boot1',window,0 if window==0 else B.MAX_BOOT)
            q=self.pair('full-'+str(window),req=req,total=B.MAX_BOOT,parent=parent,shared=shared,nonce=str(window+1)*64)
            self.start(q);state=self.drive(q);self.assertEqual(state,0);self.finish(q,state);outputs.append(q['k'].output);parent=(q['pk'],q['pg'])
        report=B.assemble_windows(outputs,[0]*4,RUN/'assembled','1'*64);self.assertEqual(report['sha256'],sha256(self.source.read_bytes()).hexdigest())
        q=self.pair('replay-window',req=B.request('b'*32,'boot1',0),total=B.MAX_BOOT,parent=parent,shared=shared,nonce='f'*64)
        self.start(q);state=self.drive(q);self.assertEqual(state,2);self.finish(q,state);self.assertEqual(q['g'].exitcode,51);self.assertEqual(q['k'].source_reads,[])

    def test_06_role_close_failure_is_propagated_to_parent(self):
        for fault in ('image-close','directory-close','ipc-close'):
            q=self.pair(fault,fault=fault);self.start(q);state=self.drive(q);self.assertEqual(state,2);self.finish(q,state);self.assertNotEqual(q['g'].exitcode,0);self.assertEqual(len(q['k'].source_reads),2)

    def test_07_success_packet_and_exit_do_not_override_corrupt_output(self):
        q=self.pair('bad-output',mode='hold-exit');self.start(q);self.drive(q,lambda state:q['link'].returned.is_set())
        p=next(q['k'].output.glob('chunk-*.bin'));raw=bytearray(p.read_bytes());raw[-1]^=1;p.write_bytes(raw)
        q['link'].exit_release.set();state=self.drive(q);self.assertEqual(state,2);self.finish(q,state);self.assertEqual(q['g'].exitcode,0)

    def test_08_static_properties_and_reproducibility(self):
        again=S.build(RUN/'reproducible');self.assertEqual(again['sha256'],self.build['sha256'])
        self.assertFalse(self.build['runtime_loader_or_imports']);self.assertFalse(self.build['shared_library_or_constructor_or_Sony_loader_required'])
        self.assertEqual(self.build['segment_alignment'],65536);self.assertEqual(self.build['ADRP_instruction_page'],4096)

    @classmethod
    def tearDownClass(cls):
        for q in cls.pairs:
            if q['link'].thread is not None and q['link'].thread.is_alive():q['link'].release_fixture();q['link'].thread.join(timeout=12)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    report=dict(schema='fx3-own-static-worker-start-and-parent-tests-v1',status='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),failure_details=[{'test':str(t),'traceback':tb} for t,tb in result.failures+result.errors],build=getattr(Tests,'build',None),cases=getattr(Tests,'cases',[]),
        all_model_threads_terminal=all(q['link'].thread is None or not q['link'].thread.is_alive() for q in getattr(Tests,'pairs',[])),
        source_hashes={p.name:sha256(p.read_bytes()).hexdigest() for p in (H/'worker.c',H/'roles_and_image.inc',H/'inner_boot_reader.c',H/'handoff_impl.inc',H/'ipc_gate.inc',H/'static_build.py',H/'static_model.py',H/'test_static_worker.py')},
        own_static_ELF_start_to_exit_executed=True,Sony_BusyBox_glibc_or_Linux_kernel_executed=False,
        actual_fork_exec_descriptor_inheritance_or_kernel_ELF_acceptance_verified=False,parent_image_hash_preexec_enforcement_implemented=False,
        new_camera_operations=0,hardware_validated=False,independent_recovery_proven=False,flashable=False)
    new_directory(RUN/'receipt',{'results.json':encode(report)})
    raise SystemExit(0 if result.wasSuccessful() else 1)
