"""Own ARM64 IPC gate; all Linux socket/credential calls below are fixtures.

The new handler reads five/six syscall registers and nested user_msghdr
pointers. No Linux syscall number is forwarded to macOS.
"""
from pathlib import Path
from hashlib import sha256
import ctypes as T
import importlib.util,json,os,struct,sys,threading,unittest,zlib
H=Path(__file__).resolve().parent;R=H.parents[2];RUN=Path(sys.argv[1]);sys.argv=[sys.argv[0],str(RUN)]
OLD=H.parent/'stage219-bound-handoff-and-request-claims'
sp=importlib.util.spec_from_file_location('previous_handoff221',OLD/'test_handoff.py');M=importlib.util.module_from_spec(sp);sys.modules[sp.name]=M;sp.loader.exec_module(M)
sp=importlib.util.spec_from_file_location('ipc_builder221',H/'dynmodule.py');D=importlib.util.module_from_spec(sp);sys.modules[sp.name]=D;sp.loader.exec_module(D)
sys.path.insert(0,str(H));import protocol as P
from fx3_recovery import boot_worker as B
from fx3_recovery.files import check_volume,new_directory,read_file,encode
A=M.M.M.A
EXPECTED=b'/bin/sh\0-c\0:\0'

def cmsg(kind,body):
    raw=struct.pack('<QII',16+len(body),1,kind)+body
    return raw.ljust((len(raw)+7)&-8,b'\0')

class Kernel(M.Kernel):
    def __init__(self,name,source,profiles,busy,parent,shared,req,nonce='c'*64,fault=None,total=B.UNIT,pid=1234):
        oldfault='block' if fault=='source-block' else fault[7:] if fault and fault.startswith('worker-') else None
        super().__init__(name,source,profiles,busy,parent,shared,req,nonce,oldfault,total,pid)
        self.ipc_fault=fault;self.cmd=EXPECTED if fault!='legacy-date' else M.M.EXPECTED
        self.ipc_calls=[];self.received=[];self.sent=[];self.polls=0;self.owned_mutations=[];self.injected=[]
        self.messages=[P.packet(1,self.hand)]
        if fault=='no-grant':self.messages=[]
        if fault=='grant-differs':
            hand=bytearray(self.hand);hand[32]^=1;struct.pack_into('<I',hand,252,zlib.crc32(hand[:252]));self.messages=[P.packet(1,bytes(hand))]
        if fault!='missing-fd':self.fds[198]={'kind':'ipc','real':None,'data':None,'pos':0,'path':None}

    def fd(self,*args,**kw):
        if self.next_fd==198:self.next_fd+=1
        return super().fd(*args,**kw)

    def syscall(self,nr,a,b,c,d):
        if nr==80 and a==198:
            if self.ipc_fault=='missing-fd':return -9
            s=M.M.M.K.M.Kstat();s.mode=0o140777;s.uid=501 if self.ipc_fault=='fd-owner' else 0;s.nlink=1;s.ino=77;s.dev=9
            if self.ipc_fault=='not-socket':s.mode=0o100600
            T.memmove(b,T.byref(s),T.sizeof(s));return 0
        if nr==57 and a==198:
            assert a not in self.closed;self.closed.append(a)
            return -5 if self.ipc_fault=='ipc-close' else 0
        if nr==57 and a in self.injected:
            assert a not in self.closed;self.closed.append(a);return 0
        return super().syscall(nr,a,b,c,d)

    def ipc(self,u,nr,args):
        self.ipc_calls.append(dict(number=nr,args=args))
        a,b,c,d,e,f=args
        def put(address,fmt,*values):u.mem_write(address,struct.pack(fmt,*values))
        def read(address,n):return bytes(u.mem_read(address,n))
        if nr==209:
            assert (a,b)==(198,1)
            if c==3:
                assert struct.unpack('<I',read(e,4))[0]==4
                put(d,'<I',1 if self.ipc_fault=='stream' else 2);put(e,'<I',4);return 0
            assert c==17 and struct.unpack('<I',read(e,4))[0]==12
            pid=self.ppid+1 if self.ipc_fault=='peer-pid' else self.ppid
            uid=501 if self.ipc_fault=='peer-uid' else 0;gid=20 if self.ipc_fault=='peer-gid' else 0
            put(d,'<III',pid,uid,gid);put(e,'<I',8 if self.ipc_fault=='peer-size' else 12);return 0
        if nr==204:
            assert a==198 and struct.unpack('<I',read(c,4))[0]==110
            put(b,'<H',2 if self.ipc_fault=='not-unix' else 1);put(c,'<I',10 if self.ipc_fault=='named' else 2);return 0
        if nr==208:
            assert (a,b,c,e)==(198,1,16,4) and read(d,4)==struct.pack('<I',1)
            self.owned_mutations.append('SO_PASSCRED');return -5 if self.ipc_fault=='passcred-error' else 0
        if nr==73:
            assert b==1 and d==0 and e==8
            fd,events,revents=struct.unpack('<ihh',read(a,8));assert fd==198 and events==1 and revents==0
            sec,ns=struct.unpack('<qq',read(c,16));assert 0<=sec<=1 and 0<=ns<1000000000
            self.polls+=1
            if self.ipc_fault=='go-block' and self.polls==2:
                self.entered.set();assert self.release.wait(timeout=10);self.now+=2_000_000_000
            if self.ipc_fault=='poll-error':return -5
            if not self.messages:return 0
            put(a+6,'<h',17 if self.ipc_fault=='poll-hup' else 1);return 1
        if nr in (211,212):
            assert a==198
            fields=struct.unpack('<QI4xQQQQI4x',read(b,56));name,namelen,iov,iovlen,control,controllen,flags=fields
            assert name==namelen==0 and iovlen==1
            base,size=struct.unpack('<QQ',read(iov,16));assert size==320
            if nr==211:
                assert c==0x4040 and control==controllen==0
                packet=read(base,320);decoded=P.decode(packet);assert decoded['hand']==self.hand
                self.sent.append(dict(kind=decoded['kind'],result=decoded['result'],sha256=sha256(packet).hexdigest()))
                if decoded['kind']==2:
                    assert self.source_opens==[] and self.source_reads==[]
                    if self.ipc_fault=='ready-short':return 319
                    if self.ipc_fault=='ready-error':return -32
                    if self.ipc_fault!='no-go':
                        hand=self.hand
                        if self.ipc_fault=='go-differs':
                            altered=bytearray(hand);altered[32]^=1;hand=bytes(altered)
                        self.messages.append(P.packet(3,hand))
                elif self.ipc_fault=='done-short':return 319
                return 320
            assert c==0x40000040 and controllen==256 and self.messages
            packet=self.messages.pop(0);which=len(self.received);self.received.append(P.decode(packet)['kind'])
            credpid=self.ppid+1 if self.ipc_fault=='message-pid' else self.ppid
            creduid=501 if self.ipc_fault=='message-uid' else 0
            credentials=cmsg(2,struct.pack('<III',credpid,creduid,0));ancillary=credentials
            if self.ipc_fault=='no-credentials':ancillary=b''
            if self.ipc_fault=='double-credentials':ancillary+=credentials
            if self.ipc_fault in ('rights','rights-truncated','rights-error'):
                ancillary+=cmsg(1,struct.pack('<ii',350,351))
                for fd in (350,351):
                    self.fds[fd]={'kind':'injected','real':None,'data':None,'pos':0,'path':None};self.injected.append(fd)
            if self.ipc_fault=='unknown-control':ancillary+=cmsg(7,b'')
            if self.ipc_fault=='bad-control-size':ancillary=struct.pack('<QII',15,1,2)+b'\0'*16
            if self.ipc_fault=='packet-reserved':
                altered=bytearray(packet);altered[288]=1;struct.pack_into('<I',altered,316,zlib.crc32(altered[:316]));packet=bytes(altered)
            if self.ipc_fault=='packet-crc':packet=packet[:-1]+bytes([packet[-1]^1])
            u.mem_write(base,packet);u.mem_write(control,ancillary)
            outflags=8 if self.ipc_fault in ('control-truncated','rights-truncated') else 32 if self.ipc_fault=='packet-truncated' else 0x40000000
            put(b+40,'<Q',len(ancillary));put(b+48,'<I',outflags)
            return -5 if self.ipc_fault=='rights-error' else 319 if self.ipc_fault=='packet-short' else 320
        raise AssertionError('unexpected IPC syscall')

class Guest(M.M.Guest):
    def interrupt(self,u,number,unused):
        nr=u.reg_read(A.UC_ARM64_REG_X8)
        if nr not in (73,204,208,209,211,212):return super().interrupt(u,number,unused)
        try:
            assert number==2
            args=[T.c_int64(u.reg_read(getattr(A,'UC_ARM64_REG_X'+str(i)))).value for i in range(6)]
            self.trace.append(dict(number=nr,args=args));result=self.kernel.ipc(u,nr,args)
            u.reg_write(A.UC_ARM64_REG_X0,result&0xffffffffffffffff)
        except BaseException as e:self.errors.append(type(e).__name__+': '+str(e));u.emu_stop()

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_volume();RUN.mkdir(mode=0o700);cls.build=D.build(RUN/'built');cls.raw=read_file(RUN/'built/boot-module.so',D.L.MAX_OBJECT)
        cls.source=OLD/'runs-final-v2/fixture/synthetic.boot';cls.profiles={};cls.cases=[];cls.guests=[]
        for path,size,digest in B.FILE_PROFILE:
            raw=read_file(R/'work/sony-firmware-20261024/stage213-AP-eMMC-boot-asset-search/originals/current-p3-initrd'/path.lstrip('/'),size)
            assert sha256(raw).hexdigest()==digest;cls.profiles[path]=raw
        p=OLD.parent/'stage218-fixed-shell-process-filter';cls.busy=read_file(p/'originals/busybox',423000);cls.parent=read_file(p/'originals/im.elf',40920)

    def make(self,name,fault=None,request=None,total=B.UNIT,base=0x10000000,shared=None,nonce='c'*64):
        req=request or B.request('b'*32,'boot0',0)
        k=Kernel(name,self.source,self.profiles,self.busy,self.parent,shared or RUN/(name+'-claims'),req,nonce=nonce,fault=fault,total=total)
        g=Guest(self.raw,k,base);g.init();self.assertEqual(g.trace,[]);self.guests.append(g);return k,g

    def case(self,name,**kw):
        k,g=self.make(name,**kw);code=g.run_worker();self.record(name,k,g,code);return k,g,code

    def record(self,name,k,g,code):
        self.assertEqual(g.errors,[]);self.assertEqual(k.errors,[]);self.assertIsNone(g.exitcode)
        expected=set(k.fds)-({198} if 198 not in k.closed else set());self.assertEqual(expected,set(k.closed))
        self.cases.append(dict(name=name,code=code,source_reads=len(k.source_reads),source_opens=k.source_opens,packets_received=k.received,packets_sent=k.sent,ipc_closed=198 in k.closed,ipc_mutations=k.owned_mutations,rights_received=k.injected,rights_closed=[fd for fd in k.injected if fd in k.closed],ipc_calls=k.ipc_calls))

    def test_01_valid_private_grant_and_GO_read_two_blocks(self):
        for i,base in enumerate((0x10000000,0x100000000)):
            k,g,code=self.case('normal-'+str(i),base=base);self.assertEqual(code,0);self.assertEqual(k.received,[1,3]);self.assertEqual([p['kind'] for p in k.sent],[2,4]);self.assertEqual(k.sent[-1]['result'],0)
            data,info=B.decode_window(k.output,code);self.assertEqual(data,self.source.read_bytes()[:B.UNIT]);self.assertEqual(len(k.source_reads),2)
            calls=len(g.trace);self.assertEqual(g.run_worker(),40);self.assertEqual(len(g.trace),calls)

    def test_02_direct_entry_and_wrong_inherited_descriptor_denied(self):
        for fault in ('missing-fd','fd-owner','not-socket','stream','not-unix','named','peer-pid','peer-uid','peer-gid','peer-size'):
            k,g,code=self.case(fault,fault=fault);self.assertNotEqual(code,0);self.assertEqual(k.source_opens,[]);self.assertEqual(k.owned_mutations,[]);self.assertNotIn(198,k.closed)

    def test_03_bad_grant_credentials_control_or_packet_never_reads(self):
        for fault in ('passcred-error','no-grant','poll-error','poll-hup','message-pid','message-uid','no-credentials','double-credentials','rights','rights-truncated','rights-error','unknown-control','bad-control-size','control-truncated','packet-truncated','packet-short','packet-reserved','packet-crc','grant-differs'):
            k,g,code=self.case(fault,fault=fault);self.assertNotEqual(code,0);self.assertEqual(k.source_opens,[]);self.assertIn(198,k.closed);self.assertEqual(set(k.injected),set(fd for fd in k.closed if fd in k.injected))

    def test_04_no_GO_or_mismatching_GO_denied_after_READY(self):
        for fault in ('ready-short','ready-error','no-go','go-differs'):
            k,g,code=self.case(fault,fault=fault);self.assertNotEqual(code,0);self.assertEqual(k.source_opens,[]);self.assertEqual(k.sent[0]['kind'],2)

    def test_05_old_date_profile_is_not_new_safe_child(self):
        k,g,code=self.case('legacy-date',fault='legacy-date');self.assertEqual(code,42);self.assertEqual(k.source_opens,[]);self.assertEqual(k.sent,[])

    def test_06_done_send_or_channel_close_failure_is_not_success(self):
        for fault in ('done-short','ipc-close'):
            k,g,code=self.case(fault,fault=fault);self.assertNotEqual(code,0);self.assertEqual(len(k.source_reads),2);self.assertEqual(k.sent[-1]['kind'],4)
            with self.assertRaises(ValueError):B.decode_window(k.output,code)

    def test_07_blocked_GO_retains_original_guest_and_channel(self):
        k,g=self.make('go-block',fault='go-block');results=[];errors=[]
        def run():
            try:results.append(g.run_worker())
            except BaseException as e:errors.append(repr(e))
        t=threading.Thread(target=run);t.start()
        try:
            self.assertTrue(k.entered.wait(timeout=5));self.assertTrue(t.is_alive());self.assertEqual(results,[]);self.assertEqual(k.source_opens,[]);self.assertNotIn(198,k.closed)
        finally:k.release.set();t.join(timeout=10)
        self.assertFalse(t.is_alive());self.assertEqual(errors,[]);self.assertEqual(results,[57]);self.record('go-block',k,g,results[0])

    def test_08_full_four_windows_survive_reserved_FD_and_exact_handoff(self):
        outputs=[];shared=RUN/'full-shared'
        for window in range(4):
            request=B.request('b'*32,'boot1',window,0 if window==0 else B.MAX_BOOT)
            k,g,code=self.case('full-'+str(window),request=request,total=B.MAX_BOOT,shared=shared,nonce=str(window+1)*64);self.assertEqual(code,0);outputs.append(k.output)
        result=B.assemble_windows(outputs,[0]*4,RUN/'assembled','1'*64)
        self.assertEqual(result['bytes'],B.MAX_BOOT);self.assertEqual(result['sha256'],sha256(self.source.read_bytes()).hexdigest());self.assertFalse(result['hardware_validated'])

    def test_09_protocol_decoder_and_reproducible_link(self):
        k,g=self.make('packet-only');raw=P.packet(4,k.hand,58);self.assertEqual(P.decode(raw)['result'],58);self.assertFalse(P.decode(raw)['trusted_launcher_or_global_owner_attested'])
        with self.assertRaises(ValueError):P.decode(raw[:-1])
        second=D.build(RUN/'reproducible');self.assertEqual(second['sha256'],self.build['sha256']);self.assertFalse(second['global_target_keeper_integrated']);self.assertTrue(second['private_inherited_datagram_gate_implemented'])
        # This case only constructs a guest; it intentionally does not enter.

    def test_10_blocked_source_keeps_channel_and_never_reports_early_done(self):
        k,g=self.make('source-block',fault='source-block');results=[];errors=[]
        def run():
            try:results.append(g.run_worker())
            except BaseException as e:errors.append(repr(e))
        t=threading.Thread(target=run);t.start()
        try:
            self.assertTrue(k.entered.wait(timeout=5));self.assertTrue(t.is_alive());self.assertEqual(results,[])
            self.assertEqual(k.received,[1,3]);self.assertEqual([p['kind'] for p in k.sent],[2]);self.assertNotIn(198,k.closed)
            self.assertFalse(any(k.fds[fd]['kind']=='source' for fd in k.closed))
        finally:k.release.set();t.join(timeout=10)
        self.assertFalse(t.is_alive());self.assertEqual(errors,[]);self.assertEqual(results,[23])
        self.assertEqual([p['kind'] for p in k.sent],[2,4]);self.assertEqual(k.sent[-1]['result'],23);self.record('source-block',k,g,results[0])

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    report=dict(schema='fx3-own-ARM64-private-IPC-gate-tests-v1',status='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),build=getattr(Tests,'build',None),cases=getattr(Tests,'cases',[]),
        guests=[dict(base=g.base,calls=g.calls,errors=g.errors,syscalls=g.trace) for g in getattr(Tests,'guests',[])],
        source_hashes={p.name:sha256(p.read_bytes()).hexdigest() for p in (H/'boot_module.c',H/'handoff_impl.inc',H/'ipc_gate.inc',H/'dynmodule.py',H/'protocol.py',H/'test_ipc_gate.py')},
        own_ARM64_executed=True,real_Linux_Sony_kernel_or_socket_credentials_verified=False,live_global_target_keeper_integrated=False,
        safe_shell_cmdline_hex=EXPECTED.hex(),safe_shell_cmdline_bytes=len(EXPECTED),new_camera_operations=0,flashable=False,independent_recovery_proven=False)
    new_directory(RUN/'receipt',{'results.json':encode(report)})
    raise SystemExit(0 if result.wasSuccessful() else 1)
