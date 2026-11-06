"""End-to-end own parent/worker ARM64 against a shared explicit fake kernel."""
from pathlib import Path
from hashlib import sha256
import json,sys,time,unittest
from paired_model import H,R,RUN,OLD,N,D,P,B,Link,ChildKernel,ParentKernel,ParentGuest,read_file,new_directory,encode,check_volume

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_volume();RUN.mkdir(mode=0o700);cls.build=D.build(RUN/'built');cls.parent_raw=read_file(RUN/'built/parent-module.so',D.L.MAX_OBJECT)
        cls.child_raw=read_file(OLD/'runs-final-v2/built/boot-module.so',D.L.MAX_OBJECT)
        assert sha256(cls.child_raw).hexdigest()=='23327fd5c43ecf44858f0705edc30db1ed795d1bc2272bf75bbeaf1ae8e8b3a3'
        cls.source=OLD.parent/'stage219-bound-handoff-and-request-claims/runs-final-v2/fixture/synthetic.boot';cls.profiles={}
        for path,size,digest in B.FILE_PROFILE:
            raw=read_file(R/'work/sony-firmware-20261024/stage213-AP-eMMC-boot-asset-search/originals/current-p3-initrd'/path.lstrip('/'),size)
            assert sha256(raw).hexdigest()==digest;cls.profiles[path]=raw
        old=OLD.parent/'stage218-fixed-shell-process-filter';cls.busy=read_file(old/'originals/busybox',423000);cls.im=read_file(old/'originals/im.elf',40920)
        cls.pairs=[];cls.parents=[];cls.cases=[];cls.pid=1234

    def pair(self,name,request=None,namespace=None,parent=None,mode=None,child_fault=None,parent_fault=None,total=B.UNIT,shared=None,nonce='c'*64,parent_pid=321):
        request=request or B.request('b'*32,'boot0',0)
        link=Link(request,parent_pid,self.pid,nonce,mode);type(self).pid+=1
        ck=ChildKernel(name+'-child',self.source,self.profiles,self.busy,self.im,shared or RUN/(name+'-claims'),link,total,child_fault)
        cg=N.Guest(self.child_raw,ck,0x10000000);cg.init();self.assertEqual(cg.trace,[])
        if parent is None:
            pk=ParentKernel(name+'-parent',self.source,self.profiles,self.im,namespace or RUN/(name+'-global'),link,parent_fault)
            pg=ParentGuest(self.parent_raw,pk);pg.init();self.assertEqual(pg.trace,[]);self.parents.append((pk,pg))
        else:pk,pg=parent;pk.prepare(link)
        pair=dict(name=name,link=link,child=ck,child_guest=cg,parent=pk,parent_guest=pg);self.pairs.append(pair);return pair

    def start(self,pair,run_child=True):
        q=pair;result=q['parent_guest'].submit(q['child'].hand,q['link'].request,q['link'].child_pid)
        if result==1 and run_child:q['link'].start_child(q['child'],q['child_guest'])
        return result

    def drive(self,pair,predicate=None,seconds=20):
        deadline=time.monotonic()+seconds;q=pair;state=None
        while time.monotonic()<deadline:
            state=q['parent_guest'].poll()
            if predicate is not None and predicate(state):return state
            if predicate is None and state in (0,2):return state
            time.sleep(.005)
        raise AssertionError('observation timeout, same guests retained: '+str(state))

    def finish(self,pair):
        q=pair;link=q['link']
        if link.thread is not None and link.thread.is_alive():
            link.release_fixture();link.thread.join(timeout=10)
        self.assertTrue(link.thread is None or not link.thread.is_alive());self.assertEqual(link.errors,[])
        if link.thread is not None:
            for _ in range(3):q['parent_guest'].poll()
            self.assertEqual(set(q['child'].fds),set(q['child'].closed))
        self.assertEqual(q['child_guest'].errors,[]);self.assertEqual(q['parent_guest'].errors,[])
        self.assertEqual(q['child'].errors,[]);self.assertEqual(q['parent'].errors,[])

    def record(self,pair,state):
        q=pair;l=q['link'];self.cases.append(dict(name=q['name'],state=state,parent_packets=list(l.parent_packets),child_packets=list(l.child_packets),child_return=l.child_return,
            child_finished=l.finished,child_reaped=l.reaped,exit_status=l.exit_status,source_reads=len(q['child'].source_reads),
            child_errors=q['child_guest'].errors,parent_errors=q['parent_guest'].errors,waits=list(q['parent'].waits),
            global_namespace=str(q['parent'].namespace),extra_received_FDs=q['parent'].injected,extra_closed_FDs=[fd for fd in q['parent'].injected if fd in q['parent'].closed]))

    def test_01_real_parent_code_drives_GRANT_READY_GO_DONE_and_normal_exit(self):
        q=self.pair('normal');self.assertEqual(self.start(q),1);self.assertEqual(self.drive(q),0);self.finish(q)
        self.assertEqual(q['link'].parent_packets,[1,3]);self.assertEqual(q['link'].child_packets,[2,4]);self.assertTrue(q['link'].reaped)
        data,info=B.decode_window(q['child'].output,0);self.assertEqual(data,self.source.read_bytes()[:B.UNIT]);self.record(q,0)
        second=self.pair('normal-next',request=B.request('c'*32,'boot0',0),parent=(q['parent'],q['parent_guest']),nonce='d'*64)
        self.assertEqual(self.start(second),1);self.assertEqual(self.drive(second),0);self.finish(second);self.record(second,0)

    def test_02_same_live_owner_full_four_windows(self):
        parent=None;outputs=[];namespace=RUN/'full-global';shared=RUN/'full-claims'
        for window in range(4):
            req=B.request('b'*32,'boot1',window,0 if window==0 else B.MAX_BOOT)
            q=self.pair('full-'+str(window),request=req,namespace=namespace,parent=parent,total=B.MAX_BOOT,shared=shared,nonce=str(window+1)*64)
            self.assertEqual(self.start(q),1);self.assertEqual(self.drive(q),0);self.finish(q);self.record(q,0)
            outputs.append(q['child'].output);parent=(q['parent'],q['parent_guest'])
        result=B.assemble_windows(outputs,[0]*4,RUN/'assembled','1'*64);self.assertEqual(result['bytes'],B.MAX_BOOT);self.assertEqual(result['sha256'],sha256(self.source.read_bytes()).hexdigest())

    def test_03_blocked_source_denies_other_job_and_other_owner_instance(self):
        namespace=RUN/'blocked-global';q=self.pair('blocked',namespace=namespace,child_fault='source-block');self.assertEqual(self.start(q),1)
        self.drive(q,lambda state:q['child'].entered.is_set());self.assertTrue(q['link'].thread.is_alive());self.assertEqual(q['link'].child_packets,[2])
        before=list(q['link'].parent_packets);req=B.request('c'*32,'boot0',0);hand=N.M.W.packet(req,2222,321,1_000_000_000,'e'*64,'f'*64)
        self.assertEqual(q['parent_guest'].submit(hand,req,2222),1);self.assertEqual(q['link'].parent_packets,before)
        other=self.pair('other-owner',namespace=namespace,parent_pid=322);self.assertEqual(self.start(other),2);self.assertEqual(other['link'].parent_packets,[]);self.finish(other);self.record(other,2)
        q['link'].release_fixture();self.assertEqual(self.drive(q),2);self.finish(q);self.record(q,2)
        q['parent_guest'].init();self.assertEqual(q['parent_guest'].poll(),2)

    def test_04_DONE_without_child_exit_keeps_owner_running(self):
        q=self.pair('done-live',mode='hold-exit');self.assertEqual(self.start(q),1)
        self.drive(q,lambda state:q['link'].returned.is_set());self.assertTrue(q['link'].thread.is_alive());self.assertFalse(q['link'].finished);self.assertEqual(q['parent_guest'].poll(),1)
        before=list(q['link'].parent_packets);self.assertEqual(q['parent_guest'].submit(q['child'].hand,q['link'].request,q['link'].child_pid),1);self.assertEqual(q['link'].parent_packets,before)
        q['link'].exit_release.set();self.assertEqual(self.drive(q),0);self.finish(q);self.record(q,0)

    def test_05_exit0_without_DONE_public_report_does_not_release(self):
        q=self.pair('no-done',mode='no-done');self.assertEqual(self.start(q),1)
        (RUN/'public-completion.json').write_text(json.dumps({'complete':True,'result':0,'pid':q['link'].child_pid}))
        self.assertEqual(self.drive(q),2);self.finish(q);self.assertTrue(q['link'].reaped);self.assertEqual(q['link'].exit_status,0);self.record(q,2)

    def test_06_duplicate_DONE_bad_exit_or_close_failure_stays_held(self):
        options=[('duplicate-done',dict(mode='duplicate-done')),('bad-exit',dict(mode='nonzero-exit')),('child-close',dict(child_fault='ipc-close')),('parent-close',dict(parent_fault='parent-close'))]
        for name,kw in options:
            q=self.pair(name,**kw);self.assertEqual(self.start(q),1);self.assertEqual(self.drive(q),2);self.finish(q);self.record(q,2)

    def test_07_bad_child_credentials_or_extra_rights_never_send_GO(self):
        for fault in ('message-pid','message-uid','rights'):
            q=self.pair(fault,parent_fault=fault);self.assertEqual(self.start(q),1);self.assertEqual(self.drive(q),2)
            self.assertEqual(q['link'].parent_packets,[1]);self.assertEqual(q['child'].source_opens,[]);self.finish(q);self.record(q,2)
            if fault=='rights':self.assertTrue(all(fd in q['parent'].closed for fd in (360,361)))

    def test_08_partial_global_claim_or_non_child_wait_blocks_GRANT_and_restart(self):
        for fault in ('record-short','record-sync','foreign-child','wait-error'):
            namespace=RUN/(fault+'-global');q=self.pair(fault,namespace=namespace,parent_fault=fault);self.assertEqual(self.start(q),2);self.assertEqual(q['link'].parent_packets,[]);self.finish(q);self.record(q,2)
            record=namespace/'owner-session.pending';self.assertTrue(record.exists());self.assertEqual(record.stat().st_size,255 if fault=='record-short' else 256)
            if fault in ('foreign-child','wait-error'):
                self.assertTrue(q['parent'].waits);self.assertEqual(q['parent'].waits[0]['returned'],-10 if fault=='foreign-child' else -4)
            other=self.pair(fault+'-restart',namespace=namespace,parent_pid=322);self.assertEqual(self.start(other),2);self.assertEqual(other['link'].parent_packets,[]);self.finish(other);self.record(other,2)

    def test_09_new_instance_cannot_reclaim_successful_owner(self):
        namespace=RUN/'completed-owner-global';q=self.pair('completed-owner',namespace=namespace);self.assertEqual(self.start(q),1);self.assertEqual(self.drive(q),0);self.finish(q);self.record(q,0)
        other=self.pair('completed-restart',namespace=namespace,parent_pid=322);self.assertEqual(self.start(other),2);self.finish(other);self.record(other,2)

    def test_10_deadline_keeps_unknown_and_eventual_completion_does_not_release(self):
        q=self.pair('late-owner',mode='hold-exit');self.assertEqual(self.start(q),1);self.drive(q,lambda state:q['link'].returned.is_set())
        q['link'].clock=121_000_000_001;self.assertEqual(q['parent_guest'].poll(),2);self.assertTrue(q['link'].thread.is_alive())
        q['link'].exit_release.set();self.finish(q);self.assertEqual(q['parent_guest'].poll(),2);self.record(q,2)

    def test_11_local_LDST32_linker_roundtrip_rejects_wrong_opcodes_and_alignment(self):
        for base in (0xb9000000,0xb9400000):
            for target in (0x40000,0x40004,0x40ffc):
                word=D.relocate(base,285,0x10000,target);self.assertEqual(((word>>10)&0xfff)*4,target&0xfff)
        for opcode,target in ((0xf9000000,0x40000),(0x94000000,0x40000),(0xb9400000,0x40002)):
            with self.assertRaises(ValueError):D.relocate(opcode,285,0x10000,target)
        again=D.build(RUN/'reproducible');self.assertEqual(again['sha256'],self.build['sha256'])

    def test_12_different_valid_parent_and_child_PIDs_are_bound_dynamically(self):
        q=self.pair('other-valid-PIDs',parent_pid=322);self.assertEqual(self.start(q),1);self.assertEqual(self.drive(q),0);self.finish(q);self.record(q,0)
        self.assertEqual(q['child'].ppid,322);self.assertEqual(q['parent'].pid,322);self.assertTrue(q['link'].reaped)

    @classmethod
    def tearDownClass(cls):
        for q in cls.pairs:
            link=q['link']
            if link.thread is not None and link.thread.is_alive():link.release_fixture();link.thread.join(timeout=12)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    report=dict(schema='fx3-paired-own-parent-worker-ARM64-tests-v1',status='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),build=getattr(Tests,'build',None),cases=getattr(Tests,'cases',[]),
        parent_guests=[dict(errors=g.errors,syscall_count=len(g.trace),call_count=len(g.calls),first_init_syscalls=g.calls[0]['syscalls'] if g.calls else None) for k,g in getattr(Tests,'parents',[])],
        all_fixture_threads_terminal=all(q['link'].thread is None or not q['link'].thread.is_alive() for q in getattr(Tests,'pairs',[])),
        source_hashes={p.name:sha256(p.read_bytes()).hexdigest() for p in (H/'parent_module.c',H/'parent_ipc.inc',H/'core_support.inc',H/'dynparent.py',H/'paired_model.py',H/'test_paired_arbiter.py')},
        own_parent_and_worker_ARM64_executed=True,all_Linux_IPC_credentials_wait4_processes_and_clock_are_fixtures=True,actual_fork_exec_loader_or_Sony_code_executed=False,
        actual_target_root_domain_or_global_exclusion_verified=False,new_camera_operations=0,hardware_validated=False,independent_recovery_proven=False,flashable=False)
    new_directory(RUN/'receipt',{'results.json':encode(report)})
    raise SystemExit(0 if result.wasSuccessful() else 1)
