"""Own boot reader C and ARM64 ELF against explicit fake Linux syscalls.

Public module files provide the reference hashes. Every device, root identity,
kernel capacity, clock and syscall is a fixture; no camera/backend is opened.
"""
from pathlib import Path
from hashlib import sha256
import ctypes as T
import importlib.util
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
from fx3_recovery import boot_worker as B
from fx3_recovery import elflink as L
from fx3_recovery.files import check_volume,new_directory,read_file,encode

RUN=Path(sys.argv[1])
sys.argv=sys.argv[:1]
spec=importlib.util.spec_from_file_location('own_boot_arm64_fixture',HERE/'tests/test_elflink.py')
G=importlib.util.module_from_spec(spec);sys.modules[spec.name]=G;spec.loader.exec_module(G)
M=G.M;M.RUN=RUN;G.RUN=RUN


class BootKernel(M.Kernel):
    def __init__(self,name,source,request,profiles,total=B.UNIT,fault=None):
        super().__init__(name,source,request,fault)
        self.total=total;self.profiles=profiles;self.source_opens=[]
        self.proc=f'major minor  #blocks  name\n\n252 126 {total//1024} nflashaB0\n252 127 {total//1024} nflashaB1\n'.encode()
        if fault=='duplicate-row':self.proc+=f'252 126 {total//1024} nflashaB0\n'.encode()
        if fault=='proc-mismatch':self.proc=self.proc.replace(f'{total//1024} nflashaB1'.encode(),b'256 nflashaB1')
        if fault=='proc-rdev':self.proc=self.proc.replace(b'252 127',b'253 127')
        if fault=='proc-zero':self.proc=self.proc.replace(str(total//1024).encode(),b'0')
        if fault=='proc-nonunit':self.proc=self.proc.replace(str(total//1024).encode(),b'129')
        if fault=='proc-overmax':self.proc=self.proc.replace(str(total//1024).encode(),b'32768')
        if fault=='proc-trailing':self.proc=self.proc[:-1]
        if fault=='proc-overflow':self.proc=self.proc.replace(b'252 127',b'4294967296 127')
        if fault=='proc-truncated':self.proc=b'x'*8192

    def syscall(self,nr,a,b,c,d):
        if nr==56:
            name=T.string_at(b).decode('ascii')
            if a==-100 and name=='/root/IAMUPDATER':
                assert c==0xa0000
                return self.fd('marker') if self.fault=='updater-marker' else -13 if self.fault=='marker-error' else -2
            if a==-100 and name in self.profiles:
                assert c==0xa0000
                if self.fault=='profile-missing':return -2
                raw=self.profiles[name]
                if self.fault=='profile-hash':raw=bytes([raw[0]^1])+raw[1:]
                if self.fault=='profile-tail':raw+=b'X'
                return self.fd('profile',data=raw,path=name)
            if a==-100 and name.startswith('/dev/'):
                assert name in ('/dev/nflashaB0','/dev/nflashaB1') and c==0xa0000
                self.source_opens.append(name)
                return self.fd('source',real=os.open(self.source,os.O_RDONLY|os.O_NOFOLLOW),path=name)
            if a!=-100 and self.fds[a]['kind']=='ram' and name=='fx3-boot-request-v1.bin':
                assert c==0xa0000;return self.fd('request',data=self.request)
        if nr==34:
            assert self.fds[a]['kind']=='ram' and c==0o700
            name=T.string_at(b).decode('ascii');assert re.fullmatch(r'fx3-boot-[0-9a-f]{32}-b[01]-w[0-3]-v1',name)
            self.output=self.root/name
            if self.fault=='existing-output':self.output.mkdir(mode=0o700)
            try:self.output.mkdir(mode=0o700)
            except FileExistsError:return -17
            return 0
        if nr==80 and self.fds[a]['kind'] in ('profile','source'):
            row=self.fds[a];s=M.Kstat();s.dev=9;s.ino=a;s.nlink=1;s.mtime=123;s.ctime=456;s.blksize=4096
            if row['kind']=='profile':
                s.mode=0o100644;s.size=len(self.profiles[row['path']])
                if self.fault=='profile-mode':s.mode=0o60660
                if self.fault=='profile-uid':s.uid=501
                if self.fault=='profile-nlink':s.nlink=2
                if self.fault=='profile-size':s.size-=1
                if self.fault=='profile-drift' and row['pos']:s.ctime+=1
            else:
                s.mode=0o60660;s.rdev=M.dev(252,126+int(row['path'][-1]))
                if self.fault=='node-type':s.mode=0o100600
                if self.fault=='node-mismatch':s.rdev=M.dev(253,133)
                if self.fault=='node-uid':s.uid=501
                if self.fault=='node-nlink':s.nlink=2
                if self.fault=='source-drift' and self.source_reads:s.ctime+=1
            T.memmove(b,T.byref(s),T.sizeof(s));return 0
        if nr==63 and self.fds[a]['kind']=='profile':
            row=self.fds[a];count=c-1 if self.fault=='profile-short' and c>1 else c
            raw=row['data'][row['pos']:row['pos']+count];row['pos']+=len(raw);T.memmove(b,raw,len(raw));return len(raw)
        if nr==29:
            assert self.fds[a]['kind']=='source' and b==0x1260
            sectors=self.total//512
            if self.fault=='size-before' or (self.fault=='size-after' and self.source_reads):sectors-=1
            T.memmove(c,struct.pack('<Q',sectors),8);return 0
        if nr==67:
            row=self.fds[a];assert row['kind']=='source' and c==B.BLOCK and 0<=d<=self.total-c
            self.source_reads.append((d,c))
            if self.fault=='block':
                self.entered.set();assert self.release.wait(timeout=10),'fixture gate requires cooperative release'
                self.now+=6_000_000_000
            if self.fault=='late':self.now+=6_000_000_000
            if self.fault=='window-late':self.now+=1_000_000_000
            raw=os.pread(row['real'],c,d)
            if self.fault=='short' and len(self.source_reads)==2:raw=raw[:-1]
            T.memmove(b,raw,len(raw))
            if self.fault=='overrun':T.memmove(b+B.BLOCK,b'X',1)
            return -5 if self.fault=='read-error' else len(raw)
        result=super().syscall(nr,a,b,c,d)
        if nr==57 and self.fault=='profile-close' and self.fds[a]['kind']=='profile':return -5
        if nr==57 and self.fault=='root-close' and self.fds[a]['kind']=='ram':return -5
        return result


class BootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_volume();RUN.mkdir(mode=0o700)
        cls.profiles={};cls.profile_paths=[]
        ref=ROOT/'work/sony-firmware-20261024/stage213-AP-eMMC-boot-asset-search/originals/current-p3-initrd'
        for path,size,digest in B.FILE_PROFILE:
            p=ref/path.lstrip('/');raw=read_file(p,size)
            assert len(raw)==size and sha256(raw).hexdigest()==digest
            cls.profiles[path]=raw;cls.profile_paths.append((p,digest))
        cls.full=b''.join(sha256(str(i).encode()).digest()*(B.BLOCK//32) for i in range(B.MAX_BOOT//B.BLOCK))
        new_directory(RUN/'fixture',{'synthetic.boot':cls.full});cls.source=RUN/'fixture/synthetic.boot'
        shim=RUN/'syscall-shim.c'
        shim.write_text('typedef long(*hook)(long,long,long,long,long);static hook h;void set_hook(hook x){h=x;}long fx3_boot_test_syscall(long n,long a,long b,long c,long d){return h?h(n,a,b,c,d):-5;}\n')
        out=RUN/'reader.dylib'
        argv=['/usr/bin/xcrun','clang','-std=c11','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector',
              '-Wall','-Wextra','-Werror','-DFX3_BOOT_HOST_FIXTURE','-dynamiclib',str(shim),
              str(HERE/'native/fx3_boot_reader.c'),'-o',str(out)]
        done=subprocess.run(argv,text=True,capture_output=True,umask=0o077)
        if done.returncode:raise RuntimeError(done.stderr)
        cls.host_build={'argv':argv,'sha256':sha256(out.read_bytes()).hexdigest(),'stderr':done.stderr}
        cls.lib=T.CDLL(str(out));cls.lib.set_hook.argtypes=[M.Kernel.CALLBACK]
        cls.lib.fx3_boot_read_window.restype=T.c_int
        cls.lib.fx3_boot_fixture_hash.argtypes=[T.c_void_p,T.c_uint32,T.c_void_p]
        cls.build=B.build_worker(RUN/'built');cls.elf=read_file(RUN/'built/worker.elf',L.MAX_OBJECT)
        cls.kernels=[];cls.guests=[]

    def kernel(self,name,fault=None,total=B.UNIT,target='boot0',window=0,expected=0,req=None):
        k=BootKernel(name,self.source,req if req is not None else B.request('5'*32,target,window,expected),self.profiles,total,fault)
        self.kernels.append(k);return k

    def worker(self,name,**kwargs):
        k=self.kernel(name,**kwargs);self.lib.fx3_boot_fixture_reset();self.lib.set_hook(k.callback)
        code=self.lib.fx3_boot_read_window();self.assertEqual(k.errors,[])
        self.assertEqual(set(k.fds),set(k.closed));return k,code

    def test_01_SHA256_vectors_and_public_modules(self):
        for data in [b'',b'abc',*[bytes(range(256))*(n//256)+bytes(range(n%256)) for n in (55,56,63,64,65,4096,1000000)],*self.profiles.values()]:
            a=T.create_string_buffer(data);out=T.create_string_buffer(32)
            self.lib.fx3_boot_fixture_hash(a,len(data),out)
            self.assertEqual(bytes(out),sha256(data).digest())

    def test_02_minimum_boot0_full_capture(self):
        k,code=self.worker('minimum');self.assertEqual(code,0)
        raw,info=B.decode_window(k.output,code);self.assertEqual(raw,self.full[:B.UNIT])
        self.assertEqual(info['selected_device'],[252,126]);self.assertEqual(k.source_opens,['/dev/nflashaB0'])
        report=B.assemble_windows([k.output],[code],RUN/'min-assembled','5'*64)
        self.assertEqual(report['sha256'],sha256(raw).hexdigest())
        for key in B.BOOT_FALSE:self.assertIs(report[key],False)
        self.assertFalse(report['atomic_snapshot_proven'])
        with self.assertRaises(FileExistsError):B.assemble_windows([k.output],[code],RUN/'min-assembled','5'*64)

    def test_03_maximum_boot1_all_four_windows_and_CLI(self):
        outputs=[]
        for window in range(4):
            k,code=self.worker('maximum-'+str(window),total=B.MAX_BOOT,target='boot1',window=window,expected=0 if window==0 else B.MAX_BOOT)
            self.assertEqual(code,0);raw,info=B.decode_window(k.output,code)
            first,count=B.shape(B.MAX_BOOT,window)
            self.assertEqual(count,128 if window<3 else 126)
            self.assertEqual(raw,self.full[first*B.BLOCK:(first+count)*B.BLOCK])
            self.assertEqual(k.source_reads,[(i*B.BLOCK,B.BLOCK) for i in range(first,first+count)])
            self.assertEqual(info['selected_device'],[252,127]);outputs.append(k.output)
        report=B.assemble_windows(outputs,[0]*4,RUN/'max-assembled','6'*64)
        self.assertEqual(report['sha256'],sha256(self.full).hexdigest())
        for name,paths in [('reordered',outputs[::-1]),('duplicate',[outputs[0]]*4),('incomplete',outputs[:3])]:
            with self.assertRaises(ValueError):B.assemble_windows(paths,[0]*len(paths),RUN/name,'6'*64)
        done=self.cli('assemble-boot-worker','--windows',*[str(p) for p in outputs],'--returns','0','0','0','0','--out',str(RUN/'cli-max'),'--body-tag','6'*64)
        self.assertEqual(done['sha256'],report['sha256'])

    def test_04_profile_and_proc_failures_before_source_open(self):
        faults=('updater-marker','marker-error','profile-missing','profile-hash','profile-tail','profile-short',
                'profile-mode','profile-uid','profile-nlink','profile-size','profile-drift','profile-close',
                'duplicate-row','proc-mismatch','proc-rdev','proc-zero','proc-nonunit','proc-overmax','proc-trailing','proc-overflow','proc-truncated')
        for fault in faults:
            with self.subTest(fault=fault):
                k,code=self.worker('pre-source-'+fault,fault=fault)
                self.assertNotEqual(code,0);self.assertEqual(k.source_opens,[]);self.assertEqual(k.source_reads,[])

    def test_05_request_identity_geometry_CRC_and_padding_denied(self):
        for offset in (0,16,32,36,40,44,48,56,88,92,96,100,104,124):
            raw=bytearray(B.request('5'*32,'boot0',0));raw[offset]^=0x80
            if offset not in (16,124):struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
            k,code=self.worker('bad-request-'+str(offset),req=bytes(raw))
            self.assertNotEqual(code,0);self.assertEqual(k.source_opens,[])
        for total in (0,B.UNIT-1,B.MAX_BOOT+1,True):
            with self.assertRaises(ValueError):B.geometry(total)
        for args in [('5'*32,'boot0',1,0),('5'*32,'boot0',1,B.UNIT),('5'*32,'p1',0,0)]:
            with self.assertRaises(ValueError):B.request(*args)
        k,code=self.worker('different-observed-total',expected=2*B.UNIT)
        self.assertNotEqual(code,0);self.assertEqual(k.source_opens,[])

    def test_06_RAM_node_capacity_and_output_guards(self):
        for fault in ('not-root','ram-symlink','persistent-fs','readonly-ram','space','negative-space',
                      'request-permissions','request-hardlink','request-short','node-type','node-mismatch',
                      'node-uid','node-nlink','size-before','existing-output'):
            with self.subTest(fault=fault):
                k,code=self.worker('pre-read-'+fault,fault=fault)
                self.assertNotEqual(code,0);self.assertEqual(k.source_reads,[])
                self.assertFalse(k.output and (k.output/'manifest.bin').exists())

    def test_07_read_faults_preserve_partial_and_never_retry(self):
        for fault in ('short','read-error','overrun','source-drift','partial-write','late','backwards','size-after','source-close'):
            with self.subTest(fault=fault):
                k,code=self.worker('during-'+fault,fault=fault)
                self.assertNotEqual(code,0);self.assertFalse((k.output/'manifest.bin').exists())
                self.assertEqual(len(k.source_reads),2 if fault in ('short','partial-write','size-after','source-close') else 1)
                if fault=='short':
                    self.assertTrue((k.output/'chunk-000.bin').is_file());self.assertFalse((k.output/'chunk-001.bin').exists())
        k,code=self.worker('window-deadline',total=B.MAX_BOOT,fault='window-late')
        self.assertNotEqual(code,0);self.assertEqual(len(k.source_reads),60)
        self.assertFalse((k.output/'manifest.bin').exists())

    def test_08_manifest_requires_separate_normal_return(self):
        for fault in ('manifest-close','manifest-fsync','root-close'):
            k,code=self.worker('manifest-'+fault,fault=fault)
            self.assertNotEqual(code,0);self.assertTrue((k.output/'manifest.bin').is_file())
            with self.assertRaises(ValueError):B.decode_window(k.output,code)
        k,code=self.worker('tamper');self.assertEqual(code,0)
        with self.assertRaises(ValueError):B.decode_window(k.output,False)
        for name,offset in [('request.bin',56),('manifest.bin',20),('manifest.bin',40),('manifest.bin',100),
                            ('manifest.bin',136),('manifest.bin',180),('manifest.bin',200),
                            ('chunk-000.bin',24),('chunk-000.bin',72),('chunk-000.bin',88),
                            ('chunk-000.bin',136),('chunk-000.bin',200),('chunk-000.bin',256)]:
            p=k.output/name;before=p.read_bytes();raw=bytearray(before);raw[offset]^=1
            try:
                p.write_bytes(raw)
                with self.assertRaises(ValueError):B.decode_window(k.output,0)
            finally:p.write_bytes(before)
        with self.assertRaises(ValueError):B.assemble_windows([k.output],[0,0],RUN/'wrong-returns','5'*64)

    def test_09_pending_call_keeps_UNKNOWN_and_entry_replay_denied(self):
        k=self.kernel('blocked',fault='block');self.lib.fx3_boot_fixture_reset();self.lib.set_hook(k.callback)
        returns=[];thread=threading.Thread(target=lambda:returns.append(self.lib.fx3_boot_read_window()))
        thread.start()
        try:
            self.assertTrue(k.entered.wait(timeout=5));self.assertTrue(thread.is_alive());self.assertEqual(returns,[])
            before=len(k.calls);self.assertEqual(self.lib.fx3_boot_read_window(),10);self.assertEqual(len(k.calls),before)
            self.assertFalse(any(k.fds[fd]['kind']=='source' for fd in k.closed))
            self.assertFalse((k.output/'manifest.bin').exists())
        finally:k.release.set();thread.join(timeout=10)
        self.assertFalse(thread.is_alive());self.assertEqual(len(k.source_reads),1);self.assertNotEqual(returns,[0])
        self.assertEqual(k.errors,[]);self.assertEqual(set(k.fds),set(k.closed))

    def test_10_current_ARM64_ELF_minimum_tail_and_profile_failure(self):
        for name,target,total,window,expected,fault in [('arm64-min','boot0',B.UNIT,0,0,None),
                ('arm64-tail','boot1',B.MAX_BOOT,3,B.MAX_BOOT,None),
                ('arm64-profile-denied','boot0',B.UNIT,0,0,'profile-hash')]:
            k=self.kernel(name,target=target,total=total,window=window,expected=expected,fault=fault)
            guest=G.Arm64Guest(self.elf,k);report=guest.run();report['name']=name;self.guests.append(report)
            if fault:self.assertNotEqual(report['worker_exitcode'],0);self.assertEqual(k.source_opens,[])
            else:
                self.assertEqual(report['worker_exitcode'],0)
                raw,info=B.decode_window(k.output,0);first,count=B.shape(total,window)
                self.assertEqual(raw,self.full[first*B.BLOCK:(first+count)*B.BLOCK])
                self.assertFalse(info['hardware_validated'])
            self.assertEqual(report['syscalls'][-1]['number'],93)

    def cli(self,*args):
        done=subprocess.run([sys.executable,'-B','-m','fx3_recovery',*args],cwd=HERE,text=True,capture_output=True)
        self.assertEqual(done.returncode,0,done.stdout+done.stderr);return json.loads(done.stdout)

    def test_11_local_CLI_build_request_and_reproducibility(self):
        info=self.cli('boot-request','--capture-id','8'*32,'--target','boot1','--window','0','--out',str(RUN/'cli-request'))
        self.assertEqual(info['camera_operations'],0);self.assertFalse(info['same_body_origin_verified'])
        self.assertEqual(read_file(RUN/'cli-request/fx3-boot-request-v1.bin',128),B.request('8'*32,'boot1',0))
        info=self.cli('build-boot-worker','--out',str(RUN/'cli-built'))
        self.assertEqual(info['sha256'],self.build['sha256']);self.assertEqual(info['camera_operations'],0)
        self.assertFalse(info['camera_launch_or_transfer_verified']);self.assertFalse(info['flashable'])
        self.assertEqual(read_file(RUN/'cli-built/worker.elf',L.MAX_OBJECT),self.elf)
        with self.assertRaises(FileExistsError):B.build_worker(RUN/'built')
        with self.assertRaises(ValueError):L.link_objects([],worker_symbol='unrecognized_entry')
        for p in ('native/fx3_boot_reader.c','native/boot_entry.S'):
            self.assertNotIn(b'fixture_reset',(RUN/'built/worker.o').read_bytes())
        self.assertEqual(sha256(read_file(HERE/'native/fx3_boot_reader.c',65536)).hexdigest(),B.SOURCE_SHA)

    @classmethod
    def tearDownClass(cls):
        assert read_file(cls.source,B.MAX_BOOT)==cls.full
        for path,digest in cls.profile_paths:assert sha256(read_file(path,400000)).hexdigest()==digest


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BootTests))
    report={'schema':'fx3-boot-worker-fixture-results-v1','status':'PASS_OFFLINE_ONLY' if result.wasSuccessful() else 'FAIL',
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'host_build':getattr(BootTests,'host_build',None),'elf_build':getattr(BootTests,'build',None),
        'cases':[{'name':k.root.name,'source_opens':k.source_opens,'source_reads':len(k.source_reads),
                  'syscalls':len(k.calls),'errors':k.errors} for k in getattr(BootTests,'kernels',[])],
        'guests':getattr(BootTests,'guests',[]),'worker_source_sha256':B.SOURCE_SHA,
        'test_source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'synthetic_source_sha256':sha256(BootTests.full).hexdigest() if hasattr(BootTests,'full') else None,
        'public_reference_file_profile':B.FILE_PROFILE,'new_camera_operations':0,
        'real_Linux_or_Sony_kernel_executed':False,**B.BOOT_FALSE}
    new_directory(RUN/'test-receipt',{'results.json':encode(report)})
    raise SystemExit(0 if result.wasSuccessful() else 1)
