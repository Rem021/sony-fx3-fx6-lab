"""Own process filter C/ARM64 with synthetic kernel process metadata only."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import ctypes as T
import importlib.util,json,struct,sys,threading,unittest
H=Path(__file__).resolve().parent;ROOT=H.parents[2];TOOL=ROOT/'outputs/fx3-recovery-adapter'
RUN=Path(sys.argv[1]);sys.argv=sys.argv[:1]
OLD=H.parent/'stage217-restricted-ET_DYN-boot-module'
sys.argv.append(str(RUN));sp=importlib.util.spec_from_file_location('previous_module_fixture218',OLD/'test_dynmodule.py')
M=importlib.util.module_from_spec(sp);sys.modules[sp.name]=M;sp.loader.exec_module(M)
M.K.RUN=RUN;M.K.M.RUN=RUN;M.K.G.RUN=RUN
sp=importlib.util.spec_from_file_location('guarded_dynmodule218',H/'dynmodule.py');D=importlib.util.module_from_spec(sp);sys.modules[sp.name]=D;sp.loader.exec_module(D)
from fx3_recovery import boot_worker as B
from fx3_recovery.files import check_volume,new_directory,read_file,encode
EXPECTED=b'/bin/sh\0-c\0/bin/date -s 070421422017.26\0'


class Kernel(M.K.BootKernel):
    def __init__(self,name,source,profiles,busybox,parent,fault=None):
        super().__init__(name,source,B.request('b'*32,'boot0',0),profiles,B.UNIT,fault)
        self.busybox=busybox;self.parent=parent;self.pid=1234;self.ppid=321;self.exe_opens={'selfexe':0,'parentexe':0};self.exe_reads=[];self.id_calls={};self.guard_paths=[]
        self.cmd=EXPECTED
        if fault=='main-im':self.cmd=b'/usr/bin/im.elf\0'
        if fault=='direct-date':self.cmd=b'\0'.join((b'/bin/date',b'-s',b'070421422017.26'))+b'\0'
        if fault=='extra-arg':self.cmd+=b'--extra\0'
        if fault=='missing-nul':self.cmd=self.cmd[:-1]
        if fault=='newline':self.cmd=self.cmd[:-1]+b'\n\0'
        if fault=='shell-options':self.cmd=self.cmd.replace(b'-c\0',b'-lc\0')
        if fault=='different-date':self.cmd=self.cmd.replace(b'0704',b'0705')
        if fault=='self-hash':self.busybox=bytes([busybox[0]^1])+busybox[1:]
        if fault=='spoof-im':self.busybox=parent
        if fault=='parent-hash':self.parent=bytes([parent[0]^1])+parent[1:]
        if fault=='self-tail':self.busybox+=b'X'

    def syscall(self,nr,a,b,c,d):
        if nr in (172,173,174,175,178):
            self.id_calls[nr]=self.id_calls.get(nr,0)+1;after=self.id_calls[nr]>1
            if nr==172:return 1 if self.fault=='bad-pid' else self.pid+int(after and self.fault=='pid-drift')
            if nr==173:return 1 if self.fault=='bad-parent-id' else self.pid if self.fault=='parent-equals-self' else self.ppid+int(after and self.fault=='parent-id-drift')
            if nr==178:return self.pid+int(self.fault=='non-main-thread' or after and self.fault=='tid-drift')
            if nr==174:return 501 if self.fault=='real-uid' or after and self.fault=='uid-drift' else 0
            if nr==175:return 501 if self.fault=='effective-uid' else 0
        if nr==56:
            path=T.string_at(b).decode('ascii')
            if a==-100 and path in ('/proc/self/cmdline','/proc/self/exe','/proc/321/exe'):
                self.guard_paths.append(path)
                if path.endswith('/cmdline'):
                    assert c==0xa0000;return self.fd('cmd',data=self.cmd,path=path)
                assert c==0x80000,'only explicitly reviewed proc-exe magic link follows allowed'
                kind='selfexe' if '/self/'in path else 'parentexe';self.exe_opens[kind]+=1
                if self.fault==kind+'-missing':return -2
                return self.fd(kind,data=self.busybox if kind=='selfexe' else self.parent,path=path)
        if nr==44 and self.fds[a]['kind']=='cmd':
            fields=[0]*32;fields[0]=0xef53 if self.fault=='not-procfs' else 0x9fa0
            T.memmove(b,struct.pack('<32Q',*fields),256);return 0
        if nr==80 and self.fds[a]['kind'] in ('cmd','selfexe','parentexe'):
            row=self.fds[a];kind=row['kind'];s=M.K.M.Kstat();s.dev=1;s.ino={'cmd':901,'selfexe':902,'parentexe':903}[kind];s.mode=0o100444 if kind=='cmd' else 0o100755;s.nlink=1;s.size=0 if kind=='cmd' else (423000 if kind=='selfexe' else 40920);s.mtime=10;s.ctime=11
            if self.fault=='spoof-im' and kind=='selfexe':s.size=len(self.busybox)
            if self.fault==kind+'-type':s.mode=0o60660
            if self.fault==kind+'-uid':s.uid=501
            if self.fault==kind+'-link':s.nlink=2
            if self.fault==kind+'-write':s.mode|=2
            if self.fault==kind+'-size':s.size+=1
            if self.fault==kind+'-drift' and row['pos']:s.ctime+=1
            if kind in self.exe_opens and self.fault==kind+'-reopen' and self.exe_opens[kind]>1:s.ino+=1
            T.memmove(b,T.byref(s),T.sizeof(s));return 0
        if nr==63 and self.fds[a]['kind'] in ('cmd','selfexe','parentexe'):
            row=self.fds[a];kind=row['kind'];count=c
            if self.fault==kind+'-short' and count>1:count=max(0,min(count,len(row['data'])-row['pos'])-1)
            if self.fault==kind+'-error':return -5
            if kind in ('selfexe','parentexe'):self.exe_reads.append((kind,row['pos'],c))
            if self.fault=='guard-block' and kind=='selfexe' and row['pos']==0:
                self.entered.set();assert self.release.wait(timeout=10),'cooperative fake release required';self.now+=11_000_000_000
            raw=row['data'][row['pos']:row['pos']+count];row['pos']+=len(raw);T.memmove(b,raw,len(raw));return len(raw)
        if nr==113:
            if self.fault=='guard-late' and self.exe_reads:self.now+=11_000_000_000
            if self.fault=='guard-backwards' and self.exe_reads:self.now=0
        result=super().syscall(nr,a,b,c,d)
        if nr==57 and self.fault==self.fds[a]['kind']+'-close':return -5
        return result


class Guest(M.Guest):
    def interrupt(self,u,number,unused):
        nr=u.reg_read(M.A.UC_ARM64_REG_X8)
        if nr not in (172,173,174,178):return super().interrupt(u,number,unused)
        try:
            assert number==2
            args=[T.c_int64(u.reg_read(getattr(M.A,'UC_ARM64_REG_X'+str(i)))).value for i in range(4)]
            self.trace.append({'number':nr,'args':args});self.kernel.calls.append((nr,*args))
            result=self.kernel.syscall(nr,*args);u.reg_write(M.A.UC_ARM64_REG_X0,result&0xffffffffffffffff)
        except BaseException as e:self.errors.append(type(e).__name__+': '+str(e));u.emu_stop()


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_volume();RUN.mkdir(mode=0o700);cls.profiles={}
        for path,size,digest in B.FILE_PROFILE:
            p=ROOT/'work/sony-firmware-20261024/stage213-AP-eMMC-boot-asset-search/originals/current-p3-initrd'/path.lstrip('/')
            raw=read_file(p,size);assert sha256(raw).hexdigest()==digest;cls.profiles[path]=raw
        cls.busybox=read_file(H/'originals/busybox',423000);cls.parent=read_file(H/'originals/im.elf',40920)
        assert sha256(cls.busybox).hexdigest()=='c3297a7086efe9a001c39fa98d74d125992cf3225cf353ab6ff2238d827c7799'
        assert sha256(cls.parent).hexdigest()=='5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91'
        cls.full=b''.join(sha256(str(i).encode()).digest()*(B.BLOCK//32) for i in range(2));new_directory(RUN/'fixture',{'synthetic.boot':cls.full});cls.source=RUN/'fixture/synthetic.boot'
        cls.build=D.build(RUN/'built');cls.raw=read_file(RUN/'built/boot-module.so',D.L.MAX_OBJECT);cls.guests=[];cls.cases=[]

    def make(self,name,fault=None,base=0x10000000):
        k=Kernel(name,self.source,self.profiles,self.busybox,self.parent,fault);g=Guest(self.raw,k,base);self.guests.append(g)
        self.assertEqual(g.status(),0);g.init();self.assertEqual(g.status(),0x4658334d4f443031);self.assertEqual(g.trace,[])
        return k,g

    def run_case(self,name,fault=None,base=0x10000000):
        k,g=self.make(name,fault,base);code=g.run_worker();self.assertFalse(g.errors);self.assertFalse(k.errors);self.assertEqual(set(k.fds),set(k.closed));self.assertIsNone(g.exitcode)
        self.cases.append(dict(name=name,code=code,guard_paths=k.guard_paths,source_opens=k.source_opens,source_reads=len(k.source_reads),syscalls=len(g.trace)))
        return k,g,code

    def denied(self,name,fault,code=None):
        k,g,result=self.run_case(name,fault)
        self.assertNotEqual(result,0)
        if code is not None:self.assertEqual(result,code)
        self.assertEqual(k.source_opens,[]);self.assertEqual(k.source_reads,[]);self.assertIsNone(k.output)
        # Failed filter must not enter the RAM request/profile/source phase.
        opens=[x for x in k.calls if x[0]==56]
        self.assertEqual(len(opens),len(k.guard_paths))
        before=len(g.trace);self.assertEqual(g.run_worker(),40);self.assertEqual(len(g.trace),before)

    def test_01_fixed_shell_profile_two_bases_then_original_reader(self):
        for n,base in enumerate((0x10000000,0x100000000)):
            k,g,code=self.run_case('positive-'+str(n),base=base);self.assertEqual(code,0)
            self.assertEqual(k.guard_paths,['/proc/self/cmdline','/proc/self/exe','/proc/321/exe','/proc/self/exe','/proc/321/exe'])
            self.assertEqual(k.exe_opens,{'selfexe':2,'parentexe':2});data,info=B.decode_window(k.output,code);self.assertEqual(data,self.full);self.assertFalse(info['same_body_origin_verified'])
            before=len(g.trace);g.init();self.assertEqual(g.run_worker(),40);self.assertEqual(len(g.trace),before)

    def test_02_main_other_shell_and_direct_date_do_not_dispatch(self):
        for fault in ('main-im','direct-date','extra-arg','missing-nul','newline','shell-options','different-date'):
            with self.subTest(fault=fault):self.denied(fault,fault,42)

    def test_03_UID_PID_and_main_thread_fail_before_proc_access(self):
        for fault in ('real-uid','effective-uid','bad-pid','bad-parent-id','parent-equals-self','non-main-thread'):
            with self.subTest(fault=fault):
                k,g,code=self.run_case(fault,fault);self.assertEqual(code,41);self.assertEqual(k.guard_paths,[]);self.assertEqual(k.source_opens,[])

    def test_04_proc_cmdline_properties_and_exact_read(self):
        for fault in ('not-procfs','cmd-type','cmd-uid','cmd-link','cmd-write','cmd-size','cmd-drift','cmd-short','cmd-error'):
            with self.subTest(fault=fault):self.denied(fault,fault,42)

    def test_05_executable_hash_metadata_and_parent_reopen(self):
        faults=('selfexe-missing','self-hash','spoof-im','self-tail','selfexe-type','selfexe-uid','selfexe-link','selfexe-write','selfexe-size','selfexe-drift','selfexe-short','selfexe-error','selfexe-reopen',
                'parentexe-missing','parent-hash','parentexe-type','parentexe-uid','parentexe-link','parentexe-write','parentexe-size','parentexe-drift','parentexe-short','parentexe-error','parentexe-reopen')
        for fault in faults:
            with self.subTest(fault=fault):self.denied(fault,fault,43 if fault.startswith('self') or fault=='spoof-im' else 44)

    def test_06_process_identity_changes_fail_before_reader(self):
        for fault in ('pid-drift','parent-id-drift','tid-drift','uid-drift'):
            with self.subTest(fault=fault):self.denied(fault,fault,41)

    def test_07_close_error_and_guard_clock_stop_without_retry(self):
        for fault in ('cmd-close','selfexe-close','parentexe-close','guard-late','guard-backwards'):
            with self.subTest(fault=fault):self.denied(fault,fault,46 if fault.endswith('-close') else 45)

    def test_08_worker_failures_still_return_without_exiting_process(self):
        for fault in ('profile-hash','updater-marker','late','manifest-close'):
            k,g,code=self.run_case('worker-'+fault,fault);self.assertNotEqual(code,0)
            if k.output:
                with self.assertRaises(ValueError):B.decode_window(k.output,code)
            self.assertEqual(len(k.source_reads),0 if fault in ('profile-hash','updater-marker') else 1 if fault=='late' else 2)

    def test_09_blocked_filter_keeps_same_guest_and_no_boot_access(self):
        k,g=self.make('blocked-filter','guard-block');returned=[];errors=[]
        def run():
            try:returned.append(g.run_worker())
            except BaseException as e:errors.append(repr(e))
        thread=threading.Thread(target=run);thread.start()
        try:
            self.assertTrue(k.entered.wait(timeout=5));self.assertTrue(thread.is_alive());self.assertEqual(returned,[]);self.assertEqual(k.source_opens,[])
            self.assertFalse(any(k.fds[x]['kind']=='selfexe' for x in k.closed));self.assertIsNone(k.output)
        finally:k.release.set();thread.join(timeout=10)
        self.assertFalse(thread.is_alive());self.assertEqual(errors,[]);self.assertEqual(returned,[45]);self.assertEqual(k.source_opens,[]);self.assertEqual(set(k.fds),set(k.closed))
        self.cases.append(dict(name='blocked-filter',code=returned[0],source_reads=0,guard_paths=k.guard_paths,source_opens=[]))

    def test_10_reproducibility_and_no_unfiltered_dynamic_export(self):
        from elftools.elf.elffile import ELFFile
        e=ELFFile(BytesIO(self.raw));names=[s.name for s in e.get_section_by_name('.dynsym').iter_symbols()]
        self.assertEqual(names,['','fx3_boot_read_window','fx3_module_status']);self.assertNotIn('fx3_inner_boot_read_window',names)
        second=D.build(RUN/'reproducible');self.assertEqual(second['sha256'],self.build['sha256'])
        self.assertTrue(second['fixed_shell_process_filter_implemented']);self.assertFalse(second['exclusive_request_attestation_verified']);self.assertFalse(second['actual_Sony_loader_acceptance_verified'])
        with self.assertRaises(FileExistsError):D.build(RUN/'built')

    @classmethod
    def tearDownClass(cls):
        assert read_file(cls.source,B.UNIT)==cls.full
        assert sha256(read_file(H/'originals/busybox',423000)).hexdigest()=='c3297a7086efe9a001c39fa98d74d125992cf3225cf353ab6ff2238d827c7799'


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    report=dict(schema='fx3-fixed-shell-process-filter-fixture-v1',status='PASS_OWN_PROCESS_FILTER_FIXTURE' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        build=getattr(Tests,'build',None),cases=getattr(Tests,'cases',[]),
        guests=[dict(base=g.base,calls=g.calls,syscalls=g.trace,errors=g.errors,source_reads=g.kernel.source_reads) for g in getattr(Tests,'guests',[])],
        expected_cmdline_hex=EXPECTED.hex(),parent_profile_is_reference_assumption_not_current_observation=True,
        original_Sony_code_executed=False,own_ARM64_code_executed=True,real_glibc_Sony_loader_or_Linux_kernel_executed=False,
        test_source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),builder_source_sha256=sha256((H/'dynmodule.py').read_bytes()).hexdigest(),camera_operations=0,**B.BOOT_FALSE)
    new_directory(RUN/'receipt',{'results.json':encode(report)})
    raise SystemExit(0 if result.wasSuccessful() else 1)
