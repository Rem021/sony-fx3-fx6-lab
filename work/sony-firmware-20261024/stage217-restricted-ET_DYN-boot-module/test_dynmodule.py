"""Own ET_DYN mapped by a declared test loader; no Sony loader/kernel execution."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import ctypes as T
import importlib.util,json,os,struct,sys,time,unittest
import unicorn as U
from unicorn import arm64_const as A
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
H=Path(__file__).resolve().parent;ROOT=H.parents[2];TOOL=ROOT/'outputs/fx3-recovery-adapter'
sys.path.insert(0,str(H));import dynmodule as D
RUN=Path(sys.argv[1]);sys.argv=sys.argv[:1]
# Import definitions only; the foreign test file does not execute its suite.
sys.argv.append(str(RUN));spec=importlib.util.spec_from_file_location('own_boot217_kernel',TOOL/'tests/test_boot_worker.py')
K=importlib.util.module_from_spec(spec);sys.modules[spec.name]=K;spec.loader.exec_module(K)
K.RUN=RUN;K.M.RUN=RUN;K.G.RUN=RUN
from fx3_recovery.files import check_volume,new_directory,read_file,encode
from fx3_recovery import boot_worker as B


class Guest(K.G.Arm64Guest):
    """Own minimal loader applies the admitted RELATIVE, then seals RELRO.

    It does not reproduce glibc's lookup/namespace/constructor scheduling,
    secure mode, Linux mmap or Sony runtime behavior.
    """
    def __init__(self,raw,kernel,base):
        assert base%65536==0
        self.raw=raw;self.kernel=kernel;self.base=base;self.report=D.inspect(raw)
        self.exitcode=None;self.errors=[];self.trace=[];self.calls=[]
        self.u=U.Uc(U.UC_ARCH_ARM64,U.UC_MODE_ARM)
        for s in self.report['segments']:
            perms=(U.UC_PROT_READ if s['flags']&4 else 0)|(U.UC_PROT_WRITE if s['flags']&2 else 0)|(U.UC_PROT_EXEC if s['flags']&1 else 0)
            self.u.mem_map(base+s['va'],D.align(s['memsz'],D.PAGE),perms)
            if s['filesz']:self.u.mem_write(base+s['va'],raw[s['offset']:s['offset']+s['filesz']])
        for r in self.report['runtime_relocations']:
            assert r['type']==1027 and r['symbol']==0
            self.u.mem_write(base+r['offset'],struct.pack('<Q',base+r['addend']))
        self.u.mem_protect(base+0x30000,D.PAGE,U.UC_PROT_READ)
        self.u.mem_map(0x70000000,0x20000,U.UC_PROT_READ|U.UC_PROT_WRITE)
        self.u.reg_write(A.UC_ARM64_REG_CPACR_EL1,3<<20)
        self.stop=0x71000000;self.u.mem_map(self.stop,4096,U.UC_PROT_READ|U.UC_PROT_EXEC)
        self.u.hook_add(U.UC_HOOK_INTR,self.interrupt)

    def call(self,va):
        self.u.reg_write(A.UC_ARM64_REG_SP,0x70020000);self.u.reg_write(A.UC_ARM64_REG_X30,self.stop)
        saved={n:0xabc0000000000000+n for n in range(19,30)}
        for n,value in saved.items():self.u.reg_write(getattr(A,'UC_ARM64_REG_X'+str(n)),value)
        start=time.monotonic();pc=self.base+va;slices=0
        while True:
            self.u.emu_start(pc,self.stop,timeout=5_000_000,count=100_000_000);slices+=1
            assert not self.errors,self.errors;assert self.exitcode is None,'module must return, not exit process'
            pc=self.u.reg_read(A.UC_ARM64_REG_PC)
            if pc==self.stop:break
            assert time.monotonic()-start<120,'own guest CPU budget; not a camera timeout'
        assert self.u.reg_read(A.UC_ARM64_REG_SP)==0x70020000
        assert all(self.u.reg_read(getattr(A,'UC_ARM64_REG_X'+str(n)))==value for n,value in saved.items())
        code=self.u.reg_read(A.UC_ARM64_REG_X0);self.calls.append(dict(va=va,result=code,source_reads=len(self.kernel.source_reads),syscalls=len(self.trace),slices=slices));return code

    def status(self):return self.call(self.report['exports']['fx3_module_status']['va'])
    def init(self):return self.call(struct.unpack('<Q',self.u.mem_read(self.base+0x30000,8))[0]-self.base)
    def run_worker(self):return self.call(self.report['exports']['fx3_boot_read_window']['va'])


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_volume();RUN.mkdir(mode=0o700)
        cls.profiles={}
        for path,size,digest in B.FILE_PROFILE:
            p=ROOT/'work/sony-firmware-20261024/stage213-AP-eMMC-boot-asset-search/originals/current-p3-initrd'/path.lstrip('/')
            raw=read_file(p,size);assert sha256(raw).hexdigest()==digest;cls.profiles[path]=raw
        cls.full=b''.join(sha256(str(i).encode()).digest()*(B.BLOCK//32) for i in range(2))
        new_directory(RUN/'fixture',{'synthetic.boot':cls.full});cls.source=RUN/'fixture/synthetic.boot'
        cls.build=D.build(RUN/'built');cls.raw=read_file(RUN/'built/boot-module.so',D.L.MAX_OBJECT);cls.kernels=[];cls.guests=[]

    def guest(self,name,base=0x10000000,fault=None):
        k=K.BootKernel(name,self.source,B.request('a'*32,'boot0',0),self.profiles,B.UNIT,fault)
        g=Guest(self.raw,k,base);self.kernels.append(k);self.guests.append(g);return k,g

    def test_01_independent_ELF_metadata_and_initializer_source(self):
        e=ELFFile(BytesIO(self.raw));self.assertEqual(e.header['e_type'],'ET_DYN');self.assertEqual(e.header['e_machine'],'EM_AARCH64')
        self.assertEqual(e.num_segments(),8);self.assertEqual(e.num_sections(),11)
        sym=e.get_section_by_name('.dynsym');self.assertEqual([s.name for s in sym.iter_symbols()],['',*D.EXPORTS])
        dynamic={t.entry.d_tag:getattr(t.entry,'d_val',None) for t in e.get_section_by_name('.dynamic').iter_tags()}
        self.assertNotIn('DT_NEEDED',dynamic);self.assertEqual(dynamic['DT_INIT_ARRAYSZ'],8)
        rel=list(e.get_section_by_name('.rela.dyn').iter_relocations());self.assertEqual(len(rel),1)
        self.assertEqual((rel[0]['r_offset'],rel[0]['r_info_sym'],rel[0]['r_info_type']),(0x30000,0,1027))
        code=self.raw[self.build['initializer_va']:self.build['initializer_va']+self.build['initializer_bytes']]
        md=Cs(CS_ARCH_ARM64,CS_MODE_ARM);ins=list(md.disasm(code,self.build['initializer_va']))
        self.assertEqual(sum(i.size for i in ins),len(code));self.assertEqual(ins[-1].mnemonic,'ret')
        self.assertFalse(any(i.mnemonic in ('svc','hvc','smc','bl','blr','br') for i in ins))
        self.assertEqual(sha256(code).hexdigest(),self.build['initializer_code_sha256'])
        self.assertFalse(self.build['actual_Sony_loader_acceptance_verified']);self.assertFalse(self.build['child_identity_guard_implemented'])

    def test_02_load_at_two_bases_init_has_no_IO_and_worker_completes(self):
        for n,base in enumerate((0x10000000,0x100000000)):
            k,g=self.guest('aslr-'+str(n),base)
            self.assertEqual(g.status(),0);self.assertEqual(g.trace,[])
            g.init();self.assertEqual(g.status(),0x4658334d4f443031);self.assertEqual(g.trace,[])
            self.assertEqual(k.source_opens,[]);self.assertEqual(g.run_worker(),0)
            self.assertEqual(k.source_reads,[(0,B.BLOCK),(B.BLOCK,B.BLOCK)])
            raw,info=B.decode_window(k.output,0);self.assertEqual(raw,self.full);self.assertFalse(info['hardware_validated'])
            self.assertEqual(set(k.fds),set(k.closed));before=len(g.trace)
            self.assertEqual(g.run_worker(),10);self.assertEqual(len(g.trace),before)
            g.init();self.assertEqual(g.run_worker(),10);self.assertEqual(len(g.trace),before)
            self.assertEqual(g.status(),0x4658334d4f443031)

    def test_03_profile_and_late_failure_returns_without_exit_or_retry(self):
        for fault in ('profile-hash','updater-marker','late','manifest-close'):
            k,g=self.guest('fault-'+fault,fault=fault);g.init();code=g.run_worker()
            self.assertNotEqual(code,0);self.assertEqual(set(k.fds),set(k.closed))
            self.assertEqual(len(k.source_reads),0 if fault in ('profile-hash','updater-marker') else 1 if fault=='late' else 2)
            self.assertFalse(k.output and (k.output/'manifest.bin').exists() and fault!='manifest-close')
            if k.output:
                with self.assertRaises(ValueError):B.decode_window(k.output,code)
            self.assertIsNone(g.exitcode)

    def test_04_RELRO_is_enforced_by_guest_CPU(self):
        k,g=self.guest('relro-write');g.u.mem_write(g.stop,struct.pack('<II',0xf9000020,0xd65f03c0))
        g.u.reg_write(A.UC_ARM64_REG_X0,1);g.u.reg_write(A.UC_ARM64_REG_X1,g.base+0x30000)
        with self.assertRaises(U.UcError) as ctx:g.u.emu_start(g.stop,g.stop+8,count=2)
        self.assertEqual(ctx.exception.errno,U.UC_ERR_WRITE_PROT);self.assertEqual(g.trace,[])

    def test_05_unknown_import_tags_RWX_and_init_relocations_rejected(self):
        muts=[]
        def at(off,fmt,value):
            b=bytearray(self.raw);struct.pack_into(fmt,b,off,value);muts.append(bytes(b))
        at(16,'<H',2);at(24,'<Q',0x10000);at(64+56+4,'<I',7)
        at(0x30008,'<q',1);at(0x30008+9*16+8,'<Q',16)
        d=dict(D.inspect(self.raw)['dynamic_tags']);at(d[7],'<Q',0x40000);at(d[7]+8,'<Q',(1<<32)|1027)
        at(d[7]+16,'<q',0x20000);at(0x30000,'<Q',0x10000);at(d[4],'<I',2)
        at(d[6]+24+8,'<Q',0x40000)
        for raw in muts:
            with self.assertRaises(ValueError):D.inspect(raw)

    def test_06_object_import_relocation_and_extra_initializer_rejected(self):
        raw=read_file(RUN/'built/module.o',D.L.MAX_OBJECT);obj=D.Object(raw)
        with self.assertRaises(ValueError):D.Object(raw.replace(b'fx3_module_status',b'bad_module_status'))
        h=D.L.HEADER.unpack_from(raw);init=next(x for x in obj.sections if x['name']=='.init_array')
        b=bytearray(raw);struct.pack_into('<Q',b,h[6]+64*init['index']+32,16)
        with self.assertRaises(ValueError):D.Object(bytes(b))
        rela=next(x for x in obj.sections if x['name']=='.rela.init_array')
        b=bytearray(raw);struct.pack_into('<I',b,rela['offset']+8,999)
        with self.assertRaises(ValueError):D.Object(bytes(b))
        b=bytearray(raw);a=struct.unpack_from('<q',raw,rela['offset']+16)[0];struct.pack_into('<q',b,rela['offset']+16,a+4)
        with self.assertRaises(ValueError):D.link(bytes(b))
        with self.assertRaises(ValueError):D.Object(b'bad')
        const=next(x for x in obj.sections if x['name'].startswith('.rodata'))
        b=bytearray(raw);struct.pack_into('<Q',b,h[6]+64*const['index']+8,3)
        with self.assertRaises(ValueError):D.Object(bytes(b))

    def test_07_reproducible_build_and_private_no_overwrite(self):
        second=D.build(RUN/'second');self.assertEqual(second['sha256'],self.build['sha256'])
        self.assertEqual(read_file(RUN/'second/boot-module.so',D.L.MAX_OBJECT),self.raw)
        self.assertEqual((RUN/'built/boot-module.so').stat().st_mode&0o777,0o600)
        with self.assertRaises(FileExistsError):D.build(RUN/'built')
        self.assertEqual(sha256(read_file(TOOL/'native/fx3_boot_reader.c',65536)).hexdigest(),B.SOURCE_SHA)

    def test_08_format_inspection_does_not_attest_initializer_behavior(self):
        report=D.inspect(self.raw);rela=dict(report['dynamic_tags'])[7]
        changed=bytearray(self.raw);struct.pack_into('<q',changed,rela+16,report['exports']['fx3_boot_read_window']['va'])
        inspected=D.inspect(bytes(changed))
        self.assertFalse(inspected['initialization_behavior_verified_by_inspector'])
        self.assertFalse(inspected['constructor_effect_authenticated_by_metadata'])
        self.assertFalse(inspected['actual_Sony_loader_acceptance_verified'])
        self.assertFalse(inspected['hardware_validated'])

    @classmethod
    def tearDownClass(cls):
        assert read_file(cls.source,B.UNIT)==cls.full
        assert all(not k.errors for k in cls.kernels)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    build=getattr(Tests,'build',None)
    report=dict(status='PASS_OWN_ET_DYN_TEST_LOADER_ONLY' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),build=build,
        guests=[dict(base=g.base,calls=g.calls,syscalls=g.trace,errors=g.errors,source_reads=g.kernel.source_reads) for g in getattr(Tests,'guests',[])],
        fake_loader_applied_runtime_relocation=True,real_glibc_or_Sony_loader_executed=False,real_Linux_kernel_executed=False,
        own_ARM64_code_executed=True,test_source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        builder_source_sha256=sha256((H/'dynmodule.py').read_bytes()).hexdigest(),camera_operations=0,**B.BOOT_FALSE)
    new_directory(RUN/'receipt',{'results.json':encode(report)})
    raise SystemExit(0 if result.wasSuccessful() else 1)
