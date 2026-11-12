"""Restricted linker tests and actual own ARM64 instructions in Unicorn.

Only the fake syscall boundary is replaced. No Sony code, real Linux kernel,
camera, USB, root helper or native execution of the Linux ELF is involved.
"""
from pathlib import Path
from hashlib import sha256
import ctypes as T
import importlib.util
import json
import os
import stat
import struct
import sys
import time
import unittest

_LOCAL_UNICORN_SITE = Path('/Volumes/KAFU2T/AI/Orca/Worktrees/Phayen/dugong/work/firmware-reverse-2026-10-22/tools/venv/lib/python3.14/site-packages')
try:
    import unicorn as U
    from unicorn import arm64_const as A
    from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
except ImportError:
    if _LOCAL_UNICORN_SITE.is_dir() and str(_LOCAL_UNICORN_SITE) not in sys.path:
        sys.path.append(str(_LOCAL_UNICORN_SITE))
    try:
        import unicorn as U
        from unicorn import arm64_const as A
        from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
    except ImportError as exc:
        U = A = Cs = None
        CS_ARCH_ARM64 = CS_MODE_ARM = 0
        _UNICORN_IMPORT_ERROR = str(exc)
    else:
        _UNICORN_IMPORT_ERROR = None
else:
    _UNICORN_IMPORT_ERROR = None

HERE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(HERE))
from fx3_recovery import elflink as L
from fx3_recovery import worker as W
from fx3_recovery import engine as E
from fx3_recovery.files import ROOT,allocate_test_run_dir,check_volume,is_clean_room_or_donor_unavailable,new_directory,read_file,encode

RUN=allocate_test_run_dir('work/sony-firmware-20261024/stage188-static-ELF-link-and-explicit-entry/runs','link-tests',__name__,sys.argv)
spec=importlib.util.spec_from_file_location('own_worker_syscall_fixture',HERE/'tests/test_worker.py')
M=importlib.util.module_from_spec(spec);sys.modules[spec.name]=M;spec.loader.exec_module(M)


class Arm64Guest:
    def __init__(self,raw,kernel):
        self.raw=raw;self.kernel=kernel;self.exitcode=None;self.errors=[];self.trace=[];self.slices=0
        self.u=U.Uc(U.UC_ARCH_ARM64,U.UC_MODE_ARM)
        self.segments=L.read_executable(raw)
        for s in self.segments:
            permissions=(U.UC_PROT_READ if s['flags']&4 else 0)|(U.UC_PROT_WRITE if s['flags']&2 else 0)|(U.UC_PROT_EXEC if s['flags']&1 else 0)
            self.u.mem_map(s['va'],L.align(s['memsz'],4096),permissions)
            if s['filesz']:self.u.mem_write(s['va'],raw[s['offset']:s['offset']+s['filesz']])
        self.u.mem_map(0x70000000,0x20000,U.UC_PROT_READ|U.UC_PROT_WRITE)
        self.u.reg_write(A.UC_ARM64_REG_SP,0x70020000)
        # Declared guest CPU capability, not an observation about FX3 state.
        self.u.reg_write(A.UC_ARM64_REG_CPACR_EL1,3<<20)
        self.entry=struct.unpack_from('<Q',raw,24)[0]
        self.u.reg_write(A.UC_ARM64_REG_PC,self.entry)
        self.u.hook_add(U.UC_HOOK_INTR,self.interrupt)

    def interrupt(self,u,number,unused):
        try:
            assert number==2,'only AArch64 SVC boundary expected'
            nr=u.reg_read(A.UC_ARM64_REG_X8)
            args=[T.c_int64(u.reg_read(getattr(A,'UC_ARM64_REG_X'+str(i)))).value for i in range(4)]
            self.trace.append({'number':nr,'args':args})
            if nr==93:
                assert 0<=args[0]<=255;self.exitcode=args[0];u.emu_stop();return
            assert nr in (29,34,44,56,57,63,64,67,80,82,113,175),'unexpected syscall'
            actual=list(args);buffers=[];copyback=[]
            def translated(index,size,output=False):
                address=args[index];raw=bytes(u.mem_read(address,size))
                storage=T.create_string_buffer(raw,size);buffers.append(storage)
                actual[index]=T.addressof(storage)
                if output:copyback.append((address,storage,size))
            if nr in (34,56):
                address=args[1];raw=bytearray()
                for i in range(512):
                    byte=u.mem_read(address+i,1)[0];raw.append(byte)
                    if not byte:break
                else:raise ValueError('unterminated guest pathname')
                storage=T.create_string_buffer(bytes(raw));buffers.append(storage);actual[1]=T.addressof(storage)
            elif nr in (44,80,113):translated(1,{44:256,80:128,113:16}[nr],True)
            elif nr==29:translated(2,8,True)
            elif nr in (63,67):
                assert 0<args[2]<=65536
                translated(1,args[2]+(32 if nr==67 else 0),True)
            elif nr==64:
                assert 0<args[2]<=65536;translated(1,args[2])
            self.kernel.calls.append((nr,*args))
            result=self.kernel.syscall(nr,*actual)
            for address,storage,size in copyback:u.mem_write(address,bytes(storage)[:size])
            u.reg_write(A.UC_ARM64_REG_X0,result&0xffffffffffffffff)
        except BaseException as error:
            self.errors.append(type(error).__name__+': '+str(error));u.emu_stop()

    def run(self):
        start=time.monotonic()
        while self.exitcode is None and not self.errors:
            if time.monotonic()-start>120:raise RuntimeError('guest CPU resource budget exceeded; not a device timeout')
            pc=self.u.reg_read(A.UC_ARM64_REG_PC)
            # Resume the SAME guest CPU after a time/count slice. Never restart
            # the entry or retry a syscall. Kernel time is an explicit fixture.
            self.u.emu_start(pc,0,timeout=5_000_000,count=100_000_000);self.slices+=1
        assert not self.errors,self.errors
        assert self.exitcode is not None
        assert set(self.kernel.fds)==set(self.kernel.closed),'guest must close returned descriptors once'
        return {'worker_exitcode':self.exitcode,'syscalls':self.trace,'slices':self.slices,
                'host_wall_seconds':time.monotonic()-start,'source_reads':self.kernel.source_reads,
                'linked_ELF_sha256':sha256(self.raw).hexdigest(),
                'AArch64_machine_code_executed':True,'real_Linux_or_Sony_kernel_executed':False,
                'CPU_FP_SIMD_enabled_as_fixture':True,'hardware_validated':False}


class LinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if _UNICORN_IMPORT_ERROR is not None:
            raise unittest.SkipTest(f'unicorn/capstone unavailable: {_UNICORN_IMPORT_ERROR}')
        donor_ref = ROOT/'work/fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1'
        if is_clean_room_or_donor_unavailable([donor_ref]):
            raise unittest.SkipTest('Clean-room mode or external FX3 2.05 donor image absent')
        check_volume();RUN.mkdir(mode=0o700)
        cls.report=L.build_worker(RUN/'built')
        cls.raw=read_file(RUN/'built/worker.elf',L.MAX_OBJECT)
        cls.objects=[(name,read_file(RUN/'built'/name,L.MAX_OBJECT)) for name in ('worker.o','entry.o')]
        cls.original=ROOT/'work/fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1'
        reference=read_file(cls.original,W.MAX_P1);cls.original_sha=sha256(reference).hexdigest()
        cls.full=reference+b'\xff'*(W.MAX_P1-len(reference))
        new_directory(RUN/'fixture',{'synthetic.p1':cls.full});cls.source=RUN/'fixture/synthetic.p1'
        cls.guests=[]

    def guest(self,name,fault=None,window=2):
        kernel=M.Kernel(name,self.source,W.request('3'*32,window),fault,run_root=RUN)
        guest=Arm64Guest(self.raw,kernel);report=guest.run();report['name']=name
        self.guests.append(report)
        return kernel,report

    def test_arm64_three_windows_execute_machine_code_and_exact_inverse(self):
        outputs=[]
        for window in range(3):
            kernel,report=self.guest('ARM64-success-'+str(window),window=window)
            self.assertEqual(report['worker_exitcode'],0)
            first,count=W.shape(window)
            self.assertEqual(kernel.source_reads,[(i*W.BLOCK,W.BLOCK) for i in range(first,first+count)])
            data,wire=W.decode_window(kernel.output,report['worker_exitcode'])
            self.assertEqual(data,self.full[first*W.BLOCK:(first+count)*W.BLOCK])
            self.assertEqual(len(wire['chunks']),count)
            self.assertEqual(report['syscalls'][-1]['number'],93)
            self.assertFalse(wire['hardware_validated']);outputs.append(kernel.output)
        report=W.assemble_worker_windows(outputs,[0,0,0],RUN/'ARM64-assembled','3'*64)
        self.assertEqual(report['sha256'],sha256(self.full).hexdigest())
        E.create_bundle(RUN/'ARM64-assembled/source.p1',RUN/'ARM64-bundle','unverified-snapshot','3'*64)
        E.rollback(RUN/'ARM64-bundle',RUN/'ARM64-bundle/candidate.p1',RUN/'ARM64-restored')
        self.assertEqual(read_file(RUN/'ARM64-restored/restored.p1',W.MAX_P1),self.full)

    def test_arm64_faults_stop_before_publication(self):
        for fault in ('not-root','persistent-fs','negative-space','node-mismatch','size-before','read-error','short','late'):
            with self.subTest(fault=fault):
                kernel,report=self.guest('ARM64-'+fault,fault)
                self.assertNotEqual(report['worker_exitcode'],0)
                self.assertFalse(kernel.output and (kernel.output/'manifest.bin').exists())
                self.assertEqual(len(kernel.source_reads),2 if fault=='short' else 1 if fault in ('read-error','late') else 0)

    def test_ELF_layout_relocation_coverage_and_reproducibility(self):
        self.assertEqual(len(self.report['relocations']),59)
        self.assertEqual(set(r['kind'] for r in self.report['relocations']),set(L.RELOCATIONS.values()))
        self.assertEqual([s['flags'] for s in self.report['segments']],[4,5,4,6])
        self.assertEqual(stat.S_IMODE((RUN/'built/worker.elf').stat().st_mode),0o600)
        second=L.build_worker(RUN/'reproducible')
        self.assertEqual(second['sha256'],self.report['sha256'])
        self.assertEqual(read_file(RUN/'reproducible/worker.elf',L.MAX_OBJECT),self.raw)
        self.assertFalse(self.report['runtime_loader_or_imports']);self.assertFalse(self.report['flashable'])

    def test_relocation_encodings_independently_disassemble(self):
        md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
        for word,kind,place,target,mnemonic,fragment in [
            (0x90000008,275,0x401000,0x400000,'adrp','#0x400000'),
            (0x91000108,277,0x401000,0x403123,'add','#0x123'),
            (0xfd400120,286,0x401000,0x403028,'ldr','#0x28'),
            (0x3dc00100,299,0x401000,0x403030,'ldr','#0x30'),
            (0x94000000,283,0x401010,0x401000,'bl','#0x401000')]:
            result=L.relocate(word,kind,place,target)
            ins=list(md.disasm(struct.pack('<I',result),place))
            self.assertEqual(len(ins),1);self.assertEqual(ins[0].mnemonic,mnemonic);self.assertIn(fragment,ins[0].op_str)
        for args in [(0,275,0x401000,0x403000),(0x91400108,277,0x401000,0x403123),
                     (0xfd400120,286,0x401000,0x403029),(0x3dc00100,299,0x401000,0x403031),
                     (0x94000000,283,0x401000,0x401002),(0x94000000,283,0x401000,0x8401000)]:
            with self.assertRaises(ValueError):L.relocate(*args)

    def test_unknown_relocation_opcode_addend_and_initializer_are_rejected(self):
        obj=L.Object(self.objects[0][1],'worker.o')
        rela=next(s for s in obj.sections if s['type']==4)
        target=obj.sections[rela['info']]
        mutations=[]
        raw=bytearray(obj.raw);struct.pack_into('<I',raw,rela['offset']+8,999);mutations.append(raw)
        raw=bytearray(obj.raw);offset=struct.unpack_from('<Q',raw,rela['offset'])[0]
        struct.pack_into('<I',raw,target['offset']+offset,0);mutations.append(raw)
        raw=bytearray(obj.raw);struct.pack_into('<q',raw,rela['offset']+16,1<<60);mutations.append(raw)
        headers=struct.unpack_from('<Q',obj.raw,40)[0]
        raw=bytearray(obj.raw);struct.pack_into('<Q',raw,headers+target['index']*64+8,7);mutations.append(raw)
        raw=bytearray(obj.raw);struct.pack_into('<I',raw,headers+target['index']*64+4,14);mutations.append(raw)
        for raw in mutations:
            with self.assertRaises(ValueError):L.link_objects([('worker.o',bytes(raw)),self.objects[1]])

    def test_external_import_and_duplicate_object_are_rejected(self):
        entry=self.objects[1][1]
        self.assertIn(b'fx3_p1_read_window',entry)
        # Keep object offsets intact: use an equal-length unrecognized name.
        changed=entry.replace(b'fx3_p1_read_window',b'xxx_p1_read_window')
        with self.assertRaises(ValueError):L.link_objects([self.objects[0],('entry.o',changed)])
        with self.assertRaises(ValueError):L.link_objects([self.objects[0],self.objects[0]])

    def test_executable_permission_entry_and_segment_corruption_rejected(self):
        mutations=[]
        raw=bytearray(self.raw);struct.pack_into('<I',raw,64+56+4,7);mutations.append(raw)
        raw=bytearray(self.raw);struct.pack_into('<Q',raw,24,0x400080);mutations.append(raw)
        raw=bytearray(self.raw);struct.pack_into('<I',raw,64,3);mutations.append(raw)
        raw=bytearray(self.raw);struct.pack_into('<Q',raw,64+56+32,len(raw)+1);mutations.append(raw)
        raw=bytearray(self.raw);struct.pack_into('<I',raw,64+56*4+4,7);mutations.append(raw)
        for raw in mutations:
            with self.assertRaises(ValueError):L.read_executable(bytes(raw))

    def test_existing_output_and_source_overwrite_denied(self):
        with self.assertRaises(FileExistsError):L.build_worker(RUN/'built')
        with self.assertRaises(FileExistsError):L.build_worker(HERE/'native/fx3_p1_reader.c')
        self.assertEqual(sha256(read_file(HERE/'native/fx3_p1_reader.c',65536)).hexdigest(),L.SOURCE_SHA)

    def test_actual_CLI_build_does_not_execute_generated_ELF(self):
        import subprocess
        done=subprocess.run([sys.executable,'-B','-m','fx3_recovery','build-worker','--out',str(RUN/'cli-built')],
                            cwd=HERE,text=True,capture_output=True)
        self.assertEqual(done.returncode,0,done.stdout+done.stderr)
        report=json.loads(done.stdout)
        self.assertEqual(report['sha256'],self.report['sha256'])
        self.assertFalse(report['AArch64_machine_code_execution_verified_by_builder'])
        self.assertFalse(report['camera_launch_or_transfer_verified'])
        self.assertEqual(report['camera_operations'],0)

    @classmethod
    def tearDownClass(cls):
        assert sha256(read_file(cls.original,W.MAX_P1)).hexdigest()==cls.original_sha


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LinkTests))
    report={'status':'PASS_STATIC_ELF_AND_ARM64_GUEST' if result.wasSuccessful() else 'FAIL',
            'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'linked_ELF_sha256':LinkTests.report['sha256'],'relocations':len(LinkTests.report['relocations']),
            'guests':LinkTests.guests,'unicorn_version':U.__version__,
            'worker_source_sha256':L.SOURCE_SHA,'entry_source_sha256':sha256(L.ENTRY_SOURCE).hexdigest(),
            'python_source_sha256':{str(p.relative_to(HERE)):sha256(p.read_bytes()).hexdigest() for p in sorted((HERE/'fx3_recovery').glob('*.py'))},
            'test_source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
            'kernel_fixture_source_sha256':sha256((HERE/'tests/test_worker.py').read_bytes()).hexdigest(),
            'new_camera_operations':0,'real_Linux_or_Sony_kernel_executed':False,'hardware_validated':False}
    new_directory(RUN/'test-receipt',{'results.json':encode(report)})
    raise SystemExit(0 if result.wasSuccessful() else 1)
