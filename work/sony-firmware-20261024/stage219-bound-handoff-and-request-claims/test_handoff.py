"""Own ARM64 handoff/claim protocol; Linux process/tmpfs are declared fixtures.

Exclusive claim creation uses actual macOS O_EXCL on ordinary local files.
This does not test root isolation, real Sony/Linux, or cross-request exclusion.
"""
from pathlib import Path
from hashlib import sha256
import ctypes as T
import select,subprocess,time
import importlib.util,json,os,re,struct,sys,threading,unittest,zlib
H=Path(__file__).resolve().parent;ROOT=H.parents[2];RUN=Path(sys.argv[1]);sys.argv=sys.argv[:1]
OLD=H.parent/'stage218-fixed-shell-process-filter';sys.argv.append(str(RUN))
sp=importlib.util.spec_from_file_location('previous_process_filter219',OLD/'test_process_filter.py');M=importlib.util.module_from_spec(sp);sys.modules[sp.name]=M;sp.loader.exec_module(M)
M.M.K.RUN=RUN;M.M.K.M.RUN=RUN;M.M.K.G.RUN=RUN
sp=importlib.util.spec_from_file_location('bound_dynmodule219',H/'dynmodule.py');D=importlib.util.module_from_spec(sp);sys.modules[sp.name]=D;sp.loader.exec_module(D)
sys.path.insert(0,str(H));import handoff as W
from fx3_recovery import boot_worker as B
from fx3_recovery.files import check_volume,new_directory,read_file,encode


class Kernel(M.Kernel):
    def __init__(self,name,source,profiles,busybox,parent,shared,req,nonce='c'*64,fault=None,total=B.UNIT,pid=1234):
        super().__init__(name,source,profiles,busybox,parent,fault)
        self.pid=pid;self.request=req;self.total=total;self.shared=shared
        self.hand=W.packet(req,pid,self.ppid,1_000_000_000,'d'*64,nonce)
        self.claim_attempts=[];self.claim_written=[];self.request_opens=0;self.handoff_paths=[]
        self.proc=f'major minor  #blocks  name\n\n252 126 {total//1024} nflashaB0\n252 127 {total//1024} nflashaB1\n'.encode()
        if fault and fault.startswith('hand-offset-'):
            off=int(fault.rsplit('-',1)[1]);raw=bytearray(self.hand);raw[off]^=0x80
            if off!=252:struct.pack_into('<I',raw,252,zlib.crc32(raw[:252]))
            self.hand=bytes(raw)
        if fault=='expired':
            raw=bytearray(self.hand);struct.pack_into('<QQ',raw,152,1,2);struct.pack_into('<I',raw,252,zlib.crc32(raw[:252]));self.hand=bytes(raw)
        if fault=='future':
            raw=bytearray(self.hand);struct.pack_into('<QQ',raw,152,5_000_000_000,6_000_000_000);struct.pack_into('<I',raw,252,zlib.crc32(raw[:252]));self.hand=bytes(raw)

    def syscall(self,nr,a,b,c,d):
        if nr==56:
            name=T.string_at(b).decode('ascii')
            if a!=-100 and self.fds[a]['kind']=='ram' and name in ('fx3-boot-handoff-v1.bin','fx3-boot-request-v1.bin','fx3-boot-claims-v1'):
                self.handoff_paths.append(name)
                if name=='fx3-boot-handoff-v1.bin':
                    assert c==0xa0000
                    return -2 if self.fault=='handoff-missing' else self.fd('handoff',data=self.hand)
                if name=='fx3-boot-request-v1.bin':
                    assert c==0xa0000;self.request_opens+=1;raw=self.request
                    if self.fault=='request-changes' and self.request_opens>1:
                        role,win=struct.unpack_from('<II',raw,36);total=struct.unpack_from('<Q',raw,48)[0];raw=B.request('e'*32,'boot'+str(role),win,total)
                    return self.fd('request',data=raw)
                assert c==0xb0000;return self.fd('claims',path=self.shared)
            if a!=-100 and self.fds[a]['kind']=='claims':
                assert c==0xa00c1 and d==0o600
                assert re.fullmatch(r'nonce-[0-9a-f]{64}\.pending|capture-[0-9a-f]{32}-b[01]-w[0-3]\.pending',name)
                self.claim_attempts.append(name);path=self.shared/name
                try:real=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
                except FileExistsError:return -17
                return self.fd('claimfile',real=real,path=path)
        if nr==34 and self.fds[a]['kind']=='ram' and T.string_at(b)==b'fx3-boot-claims-v1':
            assert c==0o700
            try:self.shared.mkdir(mode=0o700)
            except FileExistsError:return -17
            return 0
        if nr==80 and self.fds[a]['kind'] in ('handoff','claims'):
            row=self.fds[a];s=M.M.K.M.Kstat();s.dev=9;s.ino=a;s.nlink=1;s.mtime=123;s.ctime=456
            if row['kind']=='handoff':
                s.mode=0o100600;s.size=256
                if self.fault=='handoff-mode':s.mode=0o100644
                if self.fault=='handoff-link':s.nlink=2
                if self.fault=='handoff-drift' and row['pos']:s.ctime+=1
            else:
                s.mode=0o40700;s.nlink=2
                if self.fault=='claims-uid':s.uid=501
                if self.fault=='claims-mode':s.mode=0o40777
            T.memmove(b,T.byref(s),T.sizeof(s));return 0
        if nr==63 and self.fds[a]['kind']=='handoff':
            row=self.fds[a];count=c-1 if self.fault=='handoff-short' and c>1 else c;raw=row['data'][row['pos']:row['pos']+count];row['pos']+=len(raw);T.memmove(b,raw,len(raw));return len(raw)
        if nr==64 and self.fds[a]['kind']=='claimfile':
            row=self.fds[a];raw=T.string_at(b,c)
            if self.fault=='claim-short-write':raw=raw[:-1]
            n=os.write(row['real'],raw);self.claim_written.append(row['path'].name);return n
        if nr==82 and self.fds[a]['kind'] in ('claims','claimfile'):
            row=self.fds[a]
            if self.fault=='claim-sync':return -5
            if row['real'] is not None:os.fsync(row['real'])
            return 0
        if nr==57 and self.fds[a]['kind']=='claimfile':
            row=self.fds[a];assert a not in self.closed;os.close(row['real']);self.closed.append(a)
            return -5 if self.fault=='claim-close' else 0
        if nr==113 and self.fault=='after-claim-expiry' and len(self.claim_written)>=2:self.now=121_000_000_001
        if nr==82 and self.fds[a]['kind']=='output' and self.fault=='late-completion':self.now=121_000_000_001
        return super().syscall(nr,a,b,c,d)


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_volume();RUN.mkdir(mode=0o700)
        cls.profiles={}
        for path,size,digest in B.FILE_PROFILE:
            p=ROOT/'work/sony-firmware-20261024/stage213-AP-eMMC-boot-asset-search/originals/current-p3-initrd'/path.lstrip('/')
            raw=read_file(p,size);assert sha256(raw).hexdigest()==digest;cls.profiles[path]=raw
        P=H.parent/'stage218-fixed-shell-process-filter';cls.busybox=read_file(P/'originals/busybox',423000);cls.parent=read_file(P/'originals/im.elf',40920)
        cls.full=b''.join(sha256(str(i).encode()).digest()*(B.BLOCK//32) for i in range(B.MAX_BOOT//B.BLOCK))
        new_directory(RUN/'fixture',{'synthetic.boot':cls.full});cls.source=RUN/'fixture/synthetic.boot'
        cls.build=D.build(RUN/'built');cls.raw=read_file(RUN/'built/boot-module.so',D.L.MAX_OBJECT);cls.cases=[];cls.guests=[]

    def make(self,name,shared=None,req=None,nonce='c'*64,fault=None,total=B.UNIT,pid=1234):
        if shared is None:shared=RUN/(name+'-claims')
        if req is None:req=B.request('b'*32,'boot0',0)
        k=Kernel(name,self.source,self.profiles,self.busybox,self.parent,shared,req,nonce,fault,total,pid)
        g=M.Guest(self.raw,k,0x10000000);g.init();self.assertEqual(g.trace,[]);self.guests.append(g);return k,g

    def run_case(self,name,**kw):
        k,g=self.make(name,**kw);code=g.run_worker();self.assertFalse(g.errors);self.assertFalse(k.errors);self.assertEqual(set(k.fds),set(k.closed));self.assertIsNone(g.exitcode)
        self.cases.append(dict(name=name,code=code,request_opens=k.request_opens,claims=k.claim_attempts,claims_written=k.claim_written,source_reads=len(k.source_reads),source_opens=k.source_opens))
        return k,g,code

    def test_01_exact_handoff_then_full_four_window_capture(self):
        shared=RUN/'full-shared';outputs=[]
        for w in range(4):
            req=B.request('b'*32,'boot1',w,0 if w==0 else B.MAX_BOOT)
            k,g,code=self.run_case('full-'+str(w),shared=shared,req=req,nonce=(str(w+1)*64),total=B.MAX_BOOT,pid=1234+w)
            self.assertEqual(code,0);first,count=B.shape(B.MAX_BOOT,w);self.assertEqual(len(k.source_reads),count)
            data,info=B.decode_window(k.output,code);self.assertEqual(data,self.full[first*B.BLOCK:(first+count)*B.BLOCK]);outputs.append(k.output)
            self.assertEqual(k.request_opens,2);self.assertEqual(len(k.claim_written),2)
        report=B.assemble_windows(outputs,[0]*4,RUN/'assembled','1'*64);self.assertEqual(report['sha256'],sha256(self.full).hexdigest())
        self.assertFalse(report['hardware_validated']);self.assertEqual(len(list(shared.glob('*.pending'))),8)
        for p in shared.glob('*.pending'):
            row=W.decode_claim(p.read_bytes());self.assertFalse(row['operation_complete']);self.assertFalse(row['receipt_authenticated'])

    def test_02_same_window_fresh_process_and_nonce_still_denied(self):
        shared=RUN/'replay-shared';k,g,code=self.run_case('replay-first',shared=shared);self.assertEqual(code,0)
        k,g,code=self.run_case('replay-next',shared=shared,nonce='a'*64,pid=2345)
        self.assertEqual(code,51);self.assertEqual(k.source_opens,[]);self.assertEqual(k.source_reads,[])
        self.assertEqual(len(list(shared.glob('*.pending'))),3)

    def test_03_same_nonce_for_different_capture_denied(self):
        shared=RUN/'nonce-shared';k,g,code=self.run_case('nonce-first',shared=shared);self.assertEqual(code,0)
        req=B.request('a'*32,'boot0',0);k,g,code=self.run_case('nonce-next',shared=shared,req=req,pid=2345)
        self.assertEqual(code,51);self.assertEqual(k.source_opens,[])

    def test_04_PID_range_nonce_plan_SHA_clock_and_reserved_fields(self):
        for off in (0,16,32,64,96,128,132,136,140,144,148,168,176,180,184,188,252):
            k,g,code=self.run_case('field-'+str(off),fault='hand-offset-'+str(off))
            # Nonzero nonce/plan values are association data, not known secrets.
            if off in (32,64):self.assertEqual(code,0)
            else:self.assertNotEqual(code,0);self.assertEqual(k.source_opens,[])
        for fault in ('expired','future','handoff-missing','handoff-mode','handoff-link','handoff-drift','handoff-short','claims-uid','claims-mode'):
            k,g,code=self.run_case(fault,fault=fault);self.assertNotEqual(code,0);self.assertEqual(k.source_opens,[])

    def test_05_bound_request_change_after_claim_stops_before_source(self):
        k,g,code=self.run_case('request-changes',fault='request-changes')
        self.assertEqual(code,13);self.assertEqual(k.request_opens,2);self.assertEqual(k.source_opens,[]);self.assertEqual(len(k.claim_written),2)

    def test_06_partial_claim_failure_is_sticky_even_with_fresh_nonce(self):
        for fault in ('claim-short-write','claim-sync','claim-close'):
            shared=RUN/(fault+'-shared');k,g,code=self.run_case(fault,shared=shared,fault=fault)
            self.assertEqual(code,52);self.assertEqual(k.source_opens,[]);self.assertTrue(list(shared.glob('*.pending')))
            # The same nonce must not be retried after any partial claim.
            k,g,code=self.run_case(fault+'-replay',shared=shared,pid=2345)
            self.assertEqual(code,51);self.assertEqual(k.source_opens,[])
            k,g,code=self.run_case(fault+'-fresh-nonce',shared=shared,pid=3456,nonce='a'*64)
            self.assertEqual(code,51);self.assertEqual(k.source_opens,[])

    def test_07_expiry_after_claim_and_late_completion_are_not_success(self):
        for fault in ('after-claim-expiry','late-completion'):
            k,g,code=self.run_case(fault,fault=fault);self.assertEqual(code,50)
            self.assertEqual(len(k.claim_written),2)
            if fault=='after-claim-expiry':self.assertEqual(k.source_opens,[])
            else:
                self.assertTrue((k.output/'manifest.bin').exists())
                with self.assertRaises(ValueError):B.decode_window(k.output,code)

    def test_08_O_EXCL_race_same_window_allows_at_most_one_reader(self):
        shared=RUN/'race-shared';pairs=[self.make('race-'+str(i),shared=shared,nonce=str(i+5)*64,pid=3456+i) for i in range(2)]
        gate=threading.Barrier(2);results=[];errors=[]
        def run(pair):
            try:gate.wait(timeout=5);results.append((pair[0],pair[1].run_worker()))
            except BaseException as e:errors.append(repr(e))
        threads=[threading.Thread(target=run,args=(p,)) for p in pairs]
        for t in threads:t.start()
        for t in threads:t.join(timeout=30)
        self.assertTrue(all(not t.is_alive() for t in threads));self.assertEqual(errors,[]);self.assertEqual(sorted(code for k,code in results),[0,51])
        self.assertEqual(sum(len(k.source_reads) for k,code in results),2)
        for k,code in results:
            self.assertEqual(set(k.fds),set(k.closed));self.cases.append(dict(name=k.root.name,code=code,source_reads=len(k.source_reads),claims=k.claim_attempts))

    def test_09_distinct_requests_have_no_global_exclusion_counterexample(self):
        shared=RUN/'different-shared';req1=B.request('8'*32,'boot0',0);req2=B.request('9'*32,'boot0',0)
        for i,req in enumerate((req1,req2)):
            k,g,code=self.run_case('different-'+str(i),shared=shared,req=req,nonce=str(i+7)*64,pid=4567+i);self.assertEqual(code,0)
        self.assertFalse(self.build['cross_request_global_exclusion_implemented'])

    def test_10_local_packet_builder_is_not_authorization_or_completion(self):
        req=B.request('b'*32,'boot0',0);info=W.create(req,1234,321,1_000_000_000,'d'*64,RUN/'local-handoff',nonce='c'*64)
        self.assertEqual(read_file(RUN/'local-handoff/fx3-boot-handoff-v1.bin',256),W.packet(req,1234,321,1_000_000_000,'d'*64,'c'*64))
        self.assertFalse(info['trusted_launcher_or_complete_receipt_verified']);self.assertFalse(info['hardware_validated'])
        for args in [(req,1,321,1,'d'*64),(req,1234,321,0,'d'*64),(req,1234,321,1,'0'*64)]:
            with self.assertRaises(ValueError):W.packet(*args)
        with self.assertRaises(FileExistsError):W.create(req,1234,321,1,'d'*64,RUN/'local-handoff')
        second=D.build(RUN/'reproducible');self.assertEqual(second['sha256'],self.build['sha256'])
        self.assertFalse(second['exclusive_request_attestation_verified'])


    def test_11_two_real_host_processes_share_atomic_claim_namespace(self):
        shared=RUN/'real-process-shared';children=[];ready=[]
        for i in range(2):
            out=RUN/('real-child-'+str(i))
            argv=[sys.executable,'-B',str(H/'run_claim_child.py'),'--run',str(out),'--shared',str(shared),
                  '--module',str(RUN/'built/boot-module.so'),'--source',str(self.source),'--nonce',str(i+3)*64]
            child=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            children.append((child,out))
        try:
            for child,out in children:
                readable,_,_=select.select([child.stdout],[],[],15)
                self.assertTrue(readable,'owned fixture child ready timeout')
                msg=json.loads(child.stdout.readline());self.assertEqual(msg['os_pid'],child.pid);self.assertTrue(msg['ready']);ready.append(msg)
            for child,out in children:child.stdin.write('GO\n');child.stdin.flush()
            results=[]
            for child,out in children:
                stdout,stderr=child.communicate(timeout=30);self.assertEqual(child.returncode,0,stdout+stderr)
                value=json.loads((out/'child-result.json').read_text());self.assertEqual(value['os_pid'],child.pid);results.append(value)
            self.assertEqual(sorted(x['guest_result'] for x in results),[0,51]);self.assertEqual(sum(x['source_reads'] for x in results),2)
            self.assertEqual(len({x['os_pid'] for x in results}),2);self.host_process_results=results;type(self).host_process_results=results
        finally:
            for child,out in children:
                if child.poll() is None:
                    try:child.stdin.write('ABORT\n');child.stdin.flush()
                    except (BrokenPipeError,ValueError):pass
                    child.wait(timeout=30)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    report=dict(schema='fx3-bound-handoff-request-claim-tests-v1',status='PASS_OWN_HANDOFF_AND_REQUEST_CLAIM_FIXTURES' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        build=getattr(Tests,'build',None),cases=getattr(Tests,'cases',[]),guests=[dict(base=g.base,calls=g.calls,syscalls=g.trace,errors=g.errors,source_reads=g.kernel.source_reads) for g in getattr(Tests,'guests',[])],
        actual_host_O_EXCL_on_regular_files=True,real_host_process_results=getattr(Tests,'host_process_results',[]),real_root_UID_isolation_or_camera_tmpfs_verified=False,
        own_ARM64_code_executed=True,Sony_or_Linux_kernel_or_glibc_executed=False,cross_request_global_exclusion_implemented=False,
        trusted_launcher_or_complete_receipt_verified=False,test_source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),builder_source_sha256=sha256((H/'dynmodule.py').read_bytes()).hexdigest(),
        handoff_python_source_sha256=sha256((H/'handoff.py').read_bytes()).hexdigest(),camera_operations=0,**B.BOOT_FALSE)
    new_directory(RUN/'receipt',{'results.json':encode(report)})
    raise SystemExit(0 if result.wasSuccessful() else 1)
