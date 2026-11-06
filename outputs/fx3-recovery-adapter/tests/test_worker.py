"""Compiled C worker with explicit fake Linux syscalls; no hardware execution."""
from pathlib import Path
from hashlib import sha256
import ctypes as T
import json
import os
import re
import struct
import subprocess
import sys
import threading
import unittest
import zlib

HERE=Path(__file__).resolve().parent.parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from fx3_recovery import worker as W
from fx3_recovery import engine as E
from fx3_recovery.files import check_volume,new_directory,read_file,encode

RUN=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'work/sony-firmware-20261024/stage187-FX3-native-read-worker/runs/worker-tests'
sys.argv=sys.argv[:1]


class Kstat(T.Structure):
    _fields_=[('dev',T.c_uint64),('ino',T.c_uint64),('mode',T.c_uint32),('nlink',T.c_uint32),
              ('uid',T.c_uint32),('gid',T.c_uint32),('rdev',T.c_uint64),('pad1',T.c_uint64),
              ('size',T.c_int64),('blksize',T.c_int32),('pad2',T.c_int32),('blocks',T.c_int64),
              ('atime',T.c_int64),('atime_ns',T.c_uint64),('mtime',T.c_int64),('mtime_ns',T.c_uint64),
              ('ctime',T.c_int64),('ctime_ns',T.c_uint64),('pad3',T.c_uint32),('pad4',T.c_uint32)]


def dev(major,minor):
    return ((major&0xfff)<<8)|(minor&0xff)|((minor&~0xff)<<12)|((major&~0xfff)<<32)


class Kernel:
    """All Linux device/metadata calls are fake; output bytes are real files.

    Only the synthetic fixture is opened on macOS for O_RDONLY pread. Production
    syscall numbers are NEVER passed to macOS syscall().
    """
    CALLBACK=T.CFUNCTYPE(T.c_long,*([T.c_long]*5))

    def __init__(self,name,source,request,fault=None):
        self.root=RUN/name;self.root.mkdir(mode=0o700)
        self.source=source;self.request=request;self.fault=fault
        self.fds={};self.next_fd=100;self.calls=[];self.errors=[];self.source_reads=[];self.closed=[]
        self.now=1_000_000_000;self.output=None;self.entered=threading.Event();self.release=threading.Event()
        self.callback=self.CALLBACK(self.call)
        self.proc=b'major minor  #blocks  name\n\n252 1 24512 pnflasha1\n253 133 24512 cnflasha1\n'
        if fault=='duplicate-row':self.proc+=b'253 133 24512 cnflasha1\n'
        if fault=='proc-capacity':self.proc=self.proc.replace(b'24512 cnflasha1',b'24511 cnflasha1')
        if fault=='proc-trailing':self.proc=self.proc[:-1]
        if fault=='proc-overflow':self.proc=self.proc.replace(b'253 133',b'4294967296 133')

    def fd(self,kind,real=None,data=None,path=None):
        fd=self.next_fd;self.next_fd+=1
        self.fds[fd]={'kind':kind,'real':real,'data':data,'pos':0,'path':path};return fd

    def call(self,nr,a,b,c,d):
        self.calls.append((nr,a,b,c,d))
        try:return self.syscall(nr,a,b,c,d)
        except BaseException as error:
            self.errors.append(type(error).__name__+': '+str(error));return -5

    def syscall(self,nr,a,b,c,d):
        if nr==175:return 501 if self.fault=='not-root' else 0
        if nr==56:
            name=T.string_at(b).decode('ascii')
            if a==-100:
                if name=='/tmp_wbshd':
                    assert c==0xb0000
                    return -40 if self.fault=='ram-symlink' else self.fd('ram')
                assert c==0xa0000, 'source must remain O_RDONLY|CLOEXEC|NOFOLLOW'
                if name=='/proc/partitions':return self.fd('proc',data=self.proc)
                assert name=='/dev/cnflasha1','no other partition or card path admitted'
                return self.fd('source',real=os.open(self.source,os.O_RDONLY|os.O_NOFOLLOW))
            parent=self.fds[a]
            if parent['kind']=='ram':
                if name=='fx3-p1-request-v1.bin':
                    assert c==0xa0000;return self.fd('request',data=self.request)
                assert c==0xb0000 and self.output==self.root/name
                return self.fd('output',path=self.output)
            assert parent['kind']=='output' and c==0xa00c1 and d==0o600
            assert re.fullmatch(r'(request|manifest)\.bin|chunk-[0-9]{3}\.bin',name)
            path=self.output/name
            real=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            return self.fd('file',real=real,path=path)
        if nr==34:
            assert self.fds[a]['kind']=='ram' and c==0o700
            name=T.string_at(b).decode('ascii');assert re.fullmatch(r'fx3-p1-[0-9a-f]{32}-w[012]-v1',name)
            self.output=self.root/name
            if self.fault=='existing-output':self.output.mkdir(mode=0o700)
            try:self.output.mkdir(mode=0o700)
            except FileExistsError:return -17
            return 0
        if nr==44:
            row=self.fds[a];fields=[0]*32;fields[0]=0x01021994;fields[1]=4096;fields[4]=16384;fields[9]=4096
            if self.fault=='persistent-fs':fields[0]=0xef53
            if self.fault=='space':fields[4]=1
            if self.fault=='negative-space':fields[4]=0xffffffffffffffff
            if self.fault=='readonly-ram':fields[10]=1
            T.memmove(b,struct.pack('<32Q',*fields),256);return 0
        if nr==80:
            row=self.fds[a];s=Kstat();s.dev=9;s.ino=a;s.nlink=1;s.mtime=123;s.ctime=456;s.blksize=4096
            if row['kind']=='request':
                s.mode=0o100600;s.size=len(self.request)
                if self.fault=='request-permissions':s.mode=0o100644
                if self.fault=='request-hardlink':s.nlink=2
            elif row['kind']=='source':
                s.mode=0o60660;s.rdev=dev(253,133)
                if self.fault=='node-type':s.mode=0o100600
                if self.fault=='node-mismatch':s.rdev=dev(252,129)
                if self.fault=='source-drift' and self.source_reads:s.ctime+=1
            else:s.mode=0o40700;s.nlink=2
            T.memmove(b,T.byref(s),T.sizeof(s));return 0
        if nr==63:
            row=self.fds[a];assert row['kind'] in ('proc','request')
            count=c-1 if self.fault=='request-short' and row['kind']=='request' else c
            raw=row['data'][row['pos']:row['pos']+count];row['pos']+=len(raw);T.memmove(b,raw,len(raw));return len(raw)
        if nr==29:
            assert self.fds[a]['kind']=='source' and b==0x1260
            sectors=W.MAX_P1//512
            if self.fault=='size-before' or (self.fault=='size-after' and self.source_reads):sectors-=1
            T.memmove(c,struct.pack('<Q',sectors),8);return 0
        if nr==113:
            assert a==1
            self.now+=1000
            if self.fault=='backwards' and self.source_reads:self.now=1
            T.memmove(b,struct.pack('<qq',self.now//1_000_000_000,self.now%1_000_000_000),16);return 0
        if nr==67:
            row=self.fds[a];assert row['kind']=='source' and c==W.BLOCK and 0<=d<=W.MAX_P1-c
            self.source_reads.append((d,c))
            if self.fault=='block':
                self.entered.set();assert self.release.wait(timeout=10),'fixture gate not cooperatively released'
                self.now+=6_000_000_000
            if self.fault=='late':self.now+=6_000_000_000
            raw=os.pread(row['real'],c,d)
            if self.fault=='short' and len(self.source_reads)==2:raw=raw[:-1]
            T.memmove(b,raw,len(raw))
            if self.fault=='overrun':T.memmove(b+W.BLOCK,b'X',1)
            return -5 if self.fault=='read-error' else len(raw)
        if nr==64:
            row=self.fds[a];assert row['kind']=='file','writes only to new RAM-output files'
            raw=T.string_at(b,c)
            if self.fault=='partial-write' and row['path'].name=='chunk-001.bin' and c==W.BLOCK:raw=raw[:-1]
            return os.write(row['real'],raw)
        if nr==82:
            row=self.fds[a]
            if self.fault=='manifest-fsync' and row['kind']=='file' and row['path'].name=='manifest.bin':return -5
            if row['real'] is not None:os.fsync(row['real'])
            return 0
        if nr==57:
            assert a not in self.closed,'no close retry'
            row=self.fds[a];self.closed.append(a)
            if row['real'] is not None:os.close(row['real'])
            if self.fault=='source-close' and row['kind']=='source':return -5
            if self.fault=='manifest-close' and row['kind']=='file' and row['path'].name=='manifest.bin':return -5
            return 0
        raise AssertionError('unexpected syscall '+str(nr))


class WorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_volume();RUN.mkdir(mode=0o700)
        assert T.sizeof(Kstat)==128 and Kstat.size.offset==48
        cls.original=ROOT/'work/fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1'
        raw=read_file(cls.original,W.MAX_P1);cls.original_sha=sha256(raw).hexdigest()
        cls.full=raw+b'\xff'*(W.MAX_P1-len(raw));cls.expected=sha256(cls.full).hexdigest()
        new_directory(RUN/'fixture',{'synthetic.p1':cls.full});cls.source=RUN/'fixture/synthetic.p1'
        shim=RUN/'syscall-shim.c'
        shim.write_text('typedef long(*hook)(long,long,long,long,long);static hook h;void set_hook(hook x){h=x;}long fx3_p1_test_syscall(long n,long a,long b,long c,long d){return h?h(n,a,b,c,d):-5;}\n')
        cls.build=[]
        for name,args in [('host-fixture',['-DFX3_P1_HOST_FIXTURE','-dynamiclib',str(shim)]),
                          ('aarch64-object',['-target','aarch64-linux-gnu','-c'])]:
            out=RUN/('reader.dylib' if name=='host-fixture' else 'reader-aarch64.o')
            command=['xcrun','clang','-std=c11','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector',
                     '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-Wall','-Wextra','-Werror',*args,
                     str(HERE/'native/fx3_p1_reader.c'),'-o',str(out)]
            done=subprocess.run(command,text=True,capture_output=True)
            if done.returncode:raise RuntimeError(done.stderr)
            cls.build.append({'name':name,'argv':command,'sha256':sha256(out.read_bytes()).hexdigest(),'stderr':done.stderr})
        cls.lib=T.CDLL(str(RUN/'reader.dylib'));cls.lib.set_hook.argtypes=[Kernel.CALLBACK]
        cls.lib.fx3_p1_read_window.restype=T.c_int
        cls.windows=[];cls.kernels=[]

    def run_worker(self,name,fault=None,window=0,req=None):
        kernel=Kernel(name,self.source,req if req is not None else W.request('1'*32,window),fault)
        self.lib.fx3_p1_fixture_reset();self.lib.set_hook(kernel.callback)
        code=self.lib.fx3_p1_read_window();self.assertEqual(kernel.errors,[])
        self.kernels.append(kernel)
        self.assertEqual(set(kernel.fds),set(kernel.closed),'all returned calls must close their descriptors once')
        return kernel,code

    def test_three_compiled_windows_decode_build_and_exact_restore(self):
        outputs=[]
        for window in range(3):
            kernel,code=self.run_worker('success-'+str(window),window=window)
            self.assertEqual(code,0);outputs.append(kernel.output)
            data,report=W.decode_window(kernel.output,code)
            first,count=W.shape(window)
            self.assertEqual(data,self.full[first*W.BLOCK:(first+count)*W.BLOCK])
            self.assertEqual(report['selected_device'],[253,133])
            self.assertEqual(kernel.source_reads,[(i*W.BLOCK,W.BLOCK) for i in range(first,first+count)])
        report=W.assemble_worker_windows(outputs,[0,0,0],RUN/'assembled','1'*64)
        self.assertEqual(report['sha256'],self.expected);self.assertFalse(report['hardware_validated'])
        self.assertFalse(report['same_point_in_time_snapshot_proven'])
        E.create_bundle(RUN/'assembled/source.p1',RUN/'bundle','unverified-snapshot','1'*64)
        E.rollback(RUN/'bundle',RUN/'bundle/candidate.p1',RUN/'restored')
        self.assertEqual(read_file(RUN/'restored/restored.p1',W.MAX_P1),self.full)
        done=subprocess.run([sys.executable,'-B','-m','fx3_recovery','assemble-worker','--windows',*[str(p) for p in outputs],
                             '--returns','0','0','0','--body-tag','1'*64,'--out',str(RUN/'cli-assembled')],
                            cwd=HERE,text=True,capture_output=True)
        self.assertEqual(done.returncode,0,done.stdout+done.stderr)
        self.assertEqual(json.loads(done.stdout)['sha256'],self.expected)
        with self.assertRaises(ValueError):W.assemble_worker_windows(outputs[::-1],[0,0,0],RUN/'reordered','1'*64)
        with self.assertRaises(ValueError):W.assemble_worker_windows([outputs[0]]*3,[0,0,0],RUN/'duplicate','1'*64)

    def test_preconditions_reject_before_partition_read(self):
        faults=('not-root','ram-symlink','persistent-fs','readonly-ram','space','negative-space','request-permissions',
                'request-hardlink','request-short','duplicate-row','proc-capacity','proc-trailing','proc-overflow',
                'node-type','node-mismatch','size-before','existing-output')
        for fault in faults:
            with self.subTest(fault=fault):
                kernel,code=self.run_worker('pre-'+fault,fault)
                self.assertNotEqual(code,0);self.assertEqual(kernel.source_reads,[])
                self.assertFalse(kernel.output and (kernel.output/'manifest.bin').exists())

    def test_bad_request_magic_crc_and_scope_denied(self):
        for index in (0,16,32,36,40,44,48,52,56,60):
            raw=bytearray(W.request('1'*32,0));raw[index]^=0x80
            if index in (32,36,40,44,48):struct.pack_into('<I',raw,52,zlib.crc32(raw[:52]))
            kernel,code=self.run_worker('request-'+str(index),req=bytes(raw))
            self.assertNotEqual(code,0);self.assertEqual(kernel.source_reads,[])

    def test_short_error_overrun_and_identity_drift_keep_partial_without_retry(self):
        for fault in ('short','read-error','overrun','source-drift','partial-write'):
            kernel,code=self.run_worker('read-'+fault,fault)
            self.assertNotEqual(code,0);self.assertFalse((kernel.output/'manifest.bin').exists())
            self.assertEqual(len(kernel.source_reads),2 if fault in ('short','partial-write') else 1)
            if fault=='short':
                self.assertTrue((kernel.output/'chunk-000.bin').is_file())
                self.assertFalse((kernel.output/'chunk-001.bin').exists())

    def test_late_and_backwards_clock_replies_denied(self):
        for fault in ('late','backwards'):
            kernel,code=self.run_worker('time-'+fault,fault)
            self.assertNotEqual(code,0);self.assertEqual(len(kernel.source_reads),1)
            self.assertFalse((kernel.output/'manifest.bin').exists())

    def test_capacity_change_or_source_close_failure_denies_completion(self):
        for fault in ('size-after','source-close'):
            kernel,code=self.run_worker('final-'+fault,fault)
            self.assertNotEqual(code,0);self.assertEqual(len(kernel.source_reads),128)
            self.assertFalse((kernel.output/'manifest.bin').exists())

    def test_saved_manifest_does_not_override_failed_return(self):
        for fault in ('manifest-close','manifest-fsync'):
            kernel,code=self.run_worker('manifest-'+fault,fault)
            self.assertNotEqual(code,0);self.assertTrue((kernel.output/'manifest.bin').is_file())
            with self.assertRaises(ValueError):W.decode_window(kernel.output,code)

    def test_decoder_denies_mixed_scope_corrupt_payload_and_incomplete_files(self):
        kernel,code=self.run_worker('decoder-tampering')
        self.assertEqual(code,0)
        with self.assertRaises(ValueError):W.decode_window(kernel.output,False)
        for filename,offset in [('manifest.bin',56),('manifest.bin',100),('manifest.bin',108),
                                ('request.bin',52),('chunk-000.bin',24),('chunk-000.bin',72),
                                ('chunk-000.bin',104),('chunk-000.bin',128)]:
            p=kernel.output/filename;original=p.read_bytes();raw=bytearray(original);raw[offset]^=1
            try:
                p.write_bytes(raw)
                with self.assertRaises(ValueError):W.decode_window(kernel.output,0)
            finally:p.write_bytes(original)
        p=kernel.output/'chunk-127.bin';original=p.read_bytes()
        try:
            p.write_bytes(original[:-1])
            with self.assertRaises(ValueError):W.decode_window(kernel.output,0)
        finally:p.write_bytes(original)

    def test_blocked_native_call_stays_pending_without_cleanup_or_retry(self):
        kernel=Kernel('blocked-call',self.source,W.request('2'*32,0),'block')
        self.lib.fx3_p1_fixture_reset();self.lib.set_hook(kernel.callback);returned=[]
        thread=threading.Thread(target=lambda:returned.append(self.lib.fx3_p1_read_window()))
        thread.start()
        try:
            self.assertTrue(kernel.entered.wait(timeout=5));self.assertTrue(thread.is_alive())
            reads=len(kernel.source_reads);calls=len(kernel.calls)
            self.assertEqual(reads,1);self.assertEqual(returned,[])
            self.assertFalse(any(kernel.fds[fd]['kind']=='source' for fd in kernel.closed))
            self.assertFalse((kernel.output/'manifest.bin').exists())
            self.assertEqual(len(kernel.calls),calls)
        finally:kernel.release.set();thread.join(timeout=10)
        self.assertFalse(thread.is_alive());self.assertEqual(len(kernel.source_reads),1)
        self.assertNotEqual(returned,[0]);self.assertEqual(kernel.errors,[])
        self.kernels.append(kernel)

    def test_replay_of_entry_is_denied_without_new_syscall(self):
        kernel,code=self.run_worker('one-shot-entry',req=b'X'*64)
        previous=len(kernel.calls)
        self.assertEqual(self.lib.fx3_p1_read_window(),10);self.assertEqual(len(kernel.calls),previous)

    def test_native_artifact_is_relocatable_with_no_initializer_or_imports(self):
        # Parse ELF64 section/symbol metadata without installing a linker.
        raw=(RUN/'reader-aarch64.o').read_bytes()
        self.assertEqual(raw[:6],b'\x7fELF\x02\x01');self.assertEqual(struct.unpack_from('<HH',raw,16),(1,183))
        start=struct.unpack_from('<Q',raw,40)[0];size,num,names=struct.unpack_from('<HHH',raw,58)
        sections=[struct.unpack_from('<IIQQQQIIQQ',raw,start+i*size) for i in range(num)]
        name_sec=sections[names];table=raw[name_sec[4]:name_sec[4]+name_sec[5]]
        section_names=[table[s[0]:].split(b'\0',1)[0] for s in sections]
        self.assertFalse(any(n in section_names for n in (b'.init_array',b'.fini_array',b'.ctors',b'.init')))
        for s in sections:
            if s[1]!=2:continue
            strings=sections[s[6]];symbol_names=raw[strings[4]:strings[4]+strings[5]]
            for at in range(s[4]+s[9],s[4]+s[5],s[9]):
                symbol=struct.unpack_from('<IBBHQQ',raw,at)
                self.assertNotEqual(symbol[3],0,'production worker must not import libc or a loader')
                self.assertNotEqual(symbol_names[symbol[0]:].split(b'\0',1)[0],b'fx3_p1_fixture_reset')

    @classmethod
    def tearDownClass(cls):
        assert sha256(read_file(cls.original,W.MAX_P1)).hexdigest()==cls.original_sha
        assert sha256(read_file(cls.source,W.MAX_P1)).hexdigest()==cls.expected


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WorkerTests))
    report={'status':'PASS_COMPILED_WORKER_SYSCALL_FIXTURE' if result.wasSuccessful() else 'FAIL',
            'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'builds':WorkerTests.build,'cases':[{'name':k.root.name,'source_reads':len(k.source_reads),'syscalls':len(k.calls),'errors':k.errors} for k in WorkerTests.kernels],
            'synthetic_source_sha256':WorkerTests.expected,'original_reference_sha256':WorkerTests.original_sha,
            'worker_source_sha256':sha256((HERE/'native/fx3_p1_reader.c').read_bytes()).hexdigest(),
            'python_source_sha256':{str(p.relative_to(HERE)):sha256(p.read_bytes()).hexdigest() for p in sorted((HERE/'fx3_recovery').glob('*.py'))},
            'test_source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
            'AArch64_machine_code_executed':False,'production_object_only':True,
            'fake_kernel_metadata_not_physical_observation':True,'new_camera_operations':0,'hardware_validated':False}
    new_directory(RUN/'test-receipt',{'results.json':encode(report)})
    raise SystemExit(0 if result.wasSuccessful() else 1)
