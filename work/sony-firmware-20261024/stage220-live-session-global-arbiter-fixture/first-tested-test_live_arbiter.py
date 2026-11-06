"""Real ordinary Mac worker processes; source/UID/proc are fake Linux fixtures."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,select,subprocess,sys,time,unittest
from live_arbiter import H,R,OLD,FIXTURE,MODULE_SHA,LiveArbiter,Denied
sys.path.insert(0,str(R/'outputs/fx3-recovery-adapter'))
from fx3_recovery import boot_worker as B
from fx3_recovery.files import check_volume,new_directory,encode
RUN=Path(sys.argv[1]);sys.argv=sys.argv[:1]

def wait(owner,predicate,seconds=30):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        observation=owner.poll()
        if predicate(observation):return observation
        time.sleep(.01)
    raise AssertionError('same live fixture observation timeout: '+repr(observation))

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_volume();RUN.mkdir(mode=0o700);cls.owners=[];cls.events=[]

    def owner(self,name):
        o=LiveArbiter.attach(RUN/(name+'-owner'),fixture_only=True);self.owners.append(o);return o

    def request(self,capture='b',target='boot0',window=0,total=B.UNIT):
        return B.request(capture*32,target,window,total)

    def start(self,o,name,**kw):
        req=kw.pop('request',self.request());return o.start(req,RUN/name,RUN/(name+'-claims'),**kw)

    def finish(self,o):
        obs=wait(o,lambda v:o.current is None)
        self.assertTrue(all(j['process'].poll() is not None for j in o.children))
        return obs

    def test_01_full_boot0_and_boot1_each_keep_four_windows(self):
        o=self.owner('full');shared=RUN/'full-claims'
        for role in (0,1):
            outputs=[]
            for window in range(4):
                name='full-b'+str(role)+'-w'+str(window)
                request=self.request('b','boot'+str(role),window,0 if window==0 else B.MAX_BOOT)
                o.start(request,RUN/name,shared,capacity=B.MAX_BOOT)
                self.finish(o);self.assertEqual(o.state,'IDLE');d=o.history[-1]['done'];self.assertEqual(d['result'],0)
                self.assertEqual(d['source_reads'],[128,128,128,126][window]);outputs.append(Path(d['output']))
            result=B.assemble_windows(outputs,[0]*4,RUN/('assembled-b'+str(role)),'1'*64)
            self.assertEqual(result['bytes'],B.MAX_BOOT);self.assertEqual(result['sha256'],sha256((FIXTURE/'fixture/synthetic.boot').read_bytes()).hexdigest())
        self.assertEqual(len(o.history),8);self.assertTrue(o.fence.exists());self.assertEqual(len(list(shared.glob('capture-*.pending'))),8)

    def test_02_distinct_request_denied_while_original_source_is_live(self):
        o=self.owner('live');pid=self.start(o,'live-first',mode='block')
        obs=wait(o,lambda v:v.get('entered',False));self.assertTrue(obs['live']);self.assertEqual(obs['pid'],pid)
        with self.assertRaises(Denied):self.start(o,'live-second',request=self.request('c'))
        self.assertFalse((RUN/'live-second').exists());self.assertEqual(len(o.children),1)
        self.events.append(dict(test='distinct request while blocked',pid=pid,live=o.current['process'].poll() is None,second_worker_started=False))
        o.release_cooperative_fixture();self.finish(o);self.assertEqual(o.state,'HELD_UNKNOWN');self.assertEqual(o.history[-1]['done']['result'],23)
        with self.assertRaises(Denied):self.start(o,'live-after-return')

    def test_03_done_packet_alone_does_not_release_live_child(self):
        o=self.owner('done-live');self.start(o,'done-live-first',mode='post-done-wait')
        obs=wait(o,lambda v:v.get('done_received',False));self.assertTrue(obs['live']);self.assertEqual(o.state,'RUNNING')
        with self.assertRaises(Denied):self.start(o,'done-live-second')
        o.release_cooperative_fixture();self.finish(o);self.assertEqual(o.state,'IDLE')
        self.start(o,'done-live-next',request=self.request('c'));self.finish(o);self.assertEqual(o.state,'IDLE')

    def test_04_normal_exit_without_private_done_stays_unknown(self):
        o=self.owner('crash');self.start(o,'crash-first',mode='crash-before-done');self.finish(o)
        self.assertEqual(o.state,'HELD_UNKNOWN');self.assertEqual(o.history[-1]['exit'],22);self.assertIsNone(o.history[-1]['done'])
        public=json.loads((RUN/'crash-first/public-completion.json').read_text());self.assertTrue(public['complete'])
        with self.assertRaises(Denied):self.start(o,'crash-second')

    def test_05_wrong_nonce_module_or_duplicate_result_stays_unknown(self):
        for mode in ('bad-nonce','bad-module','extra-frame'):
            o=self.owner(mode);self.start(o,mode+'-first',mode=mode);self.finish(o);self.assertEqual(o.state,'HELD_UNKNOWN')
            with self.assertRaises(Denied):self.start(o,mode+'-second')

    def test_06_deadline_does_not_kill_or_free_original_process(self):
        o=self.owner('deadline');self.start(o,'deadline-first',mode='post-done-wait',deadline_seconds=1)
        obs=wait(o,lambda v:v.get('done_received',False));self.assertTrue(obs['live'])
        obs=wait(o,lambda v:v['state']=='HELD_UNKNOWN');self.assertTrue(obs['live'])
        with self.assertRaises(Denied):self.start(o,'deadline-second')
        with self.assertRaises(Denied):o.close()
        o.release_cooperative_fixture();self.finish(o);self.assertEqual(o.state,'HELD_UNKNOWN')

    def test_07_changed_public_fence_cannot_create_completion(self):
        o=self.owner('tamper');self.start(o,'tamper-first',mode='post-done-wait')
        wait(o,lambda v:v.get('done_received',False));o.fence.write_text(json.dumps({'complete':True,'state':'CLEAN'}))
        self.assertEqual(o.poll()['state'],'HELD_UNKNOWN')
        o.release_cooperative_fixture();self.finish(o);self.assertEqual(o.state,'HELD_UNKNOWN')

    def test_08_partial_owner_record_and_restart_never_resume(self):
        directory=RUN/'partial-owner'
        def partial(fd,raw):return os.write(fd,raw[:7])
        with self.assertRaises(Denied):LiveArbiter.attach(directory,fixture_only=True,writer=partial)
        self.assertEqual((directory/'global-source-session.v1.held').stat().st_size,7)
        with self.assertRaises(Denied):LiveArbiter.attach(directory,fixture_only=True)
        o=self.owner('restart');self.start(o,'restart-first');self.finish(o);self.assertEqual(o.state,'IDLE');o.close()
        with self.assertRaises(Denied):LiveArbiter.attach(o.directory,fixture_only=True)

    def test_09_real_competing_owner_process_and_dead_owner_denied(self):
        directory=RUN/'real-owner-shared';children=[]
        for i in range(2):
            p=subprocess.Popen([sys.executable,'-B',str(H/'owner_claim_child.py'),str(directory)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            children.append(p)
        try:
            replies=[]
            for p in children:
                ready,_,_=select.select([p.stdout],[],[],10);self.assertTrue(ready)
                replies.append(json.loads(p.stdout.readline()))
            self.assertEqual(sorted(x['claimed'] for x in replies),[False,True])
            for p,row in zip(children,replies):
                if row['claimed']:self.assertIsNone(p.poll());p.stdin.write('EXIT\n');p.stdin.flush()
            for p in children:
                out,err=p.communicate(timeout=10);self.assertEqual(p.returncode,0,out+err)
            with self.assertRaises(Denied):LiveArbiter.attach(directory,fixture_only=True)
            self.events.append(dict(test='real owner race and dead owner',children=replies,all_terminal=True,restart_denied=True))
        finally:
            for p in children:
                if p.poll() is None:p.stdin.write('EXIT\n');p.stdin.flush();p.wait(timeout=10)

    def test_10_no_target_backend_and_no_public_restart_reconstruction(self):
        with self.assertRaises(Denied):LiveArbiter.attach(RUN/'no-target',fixture_only=False)
        self.assertFalse((RUN/'no-target').exists())

    @classmethod
    def tearDownClass(cls):
        # A test failure does not justify killing or forgetting a live process.
        for o in cls.owners:
            if o.current is not None and o.current['process'].poll() is None:
                if o.current['entered'] or o.current['done'] is not None:o.release_cooperative_fixture()
                wait(o,lambda v:o.current is None)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    report=dict(schema='fx3-live-session-arbiter-fixture-tests-v1',status='PASS_LIVE_MEDIATED_FIXTURE_ONLY' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        owners=[dict(directory=str(o.directory),state=o.state,history=o.history,children=len(o.children),all_children_terminal=all(j['process'].poll() is not None for j in o.children)) for o in Tests.owners],events=Tests.events,
        source_hashes={p.name:sha256(p.read_bytes()).hexdigest() for p in (H/'live_arbiter.py',H/'model_worker.py',H/'test_live_arbiter.py',H/'owner_claim_child.py')},
        module_sha256=MODULE_SHA,mediated_path_has_global_live_owner=True,target_ARM64_entry_global_fence_integrated=False,
        ordinary_Mac_processes_used=True,real_target_root_UID_or_private_IPC_authority_proven=False,
        source_UID_proc_and_Linux_are_fixtures=True,Sony_or_Linux_code_executed=False,own_ARM64_code_executed=True,new_camera_operations=0,
        independent_recovery_proven=False,flashable=False,goal_complete=False,persistent_write_release=False)
    new_directory(RUN/'receipt',{'results.json':encode(report)})
    raise SystemExit(0 if result.wasSuccessful() else 1)
