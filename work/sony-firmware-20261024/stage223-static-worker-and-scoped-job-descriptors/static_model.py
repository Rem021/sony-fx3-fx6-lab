"""Own static ELF from _start; Linux exec, inheritance and credentials modeled.
No Linux syscall number is forwarded to Mac. Parent 222 binary is unchanged.
"""
from pathlib import Path
import ctypes as T
import importlib.util,json,os,struct,sys,time,zlib
from hashlib import sha256
H=Path(__file__).resolve().parent;RUN=Path(sys.argv[1]);sys.argv=[sys.argv[0],str(RUN)]
s=importlib.util.spec_from_file_location('paired222_for_static223',H.parent/'stage222-parent-arbiter-core-and-paired-ARM64/paired_model.py');M=importlib.util.module_from_spec(s);sys.modules[s.name]=M;s.loader.exec_module(M)
s=importlib.util.spec_from_file_location('static223builder',H/'static_build.py');S=importlib.util.module_from_spec(s);sys.modules[s.name]=S;s.loader.exec_module(S)
R=M.R;N=M.N;P=M.P;B=M.B;A=M.A;U=M.U;Kstat=M.Kstat;cmsg=N.cmsg
Base=N.M.M.M.K.G.Arm64Guest
from fx3_recovery.files import check_volume,new_directory,read_file,encode

class Kernel(N.Kernel):
    def __init__(self,name,source,profiles,im,shared,link,image,total=B.UNIT,fault=None,roles=(71,72,73)):
        super().__init__(name,source,profiles,im,im,shared,link.request,nonce=link.nonce,fault=fault,total=total,pid=link.child_pid)
        self.fds.pop(198);self.image_fd,self.job_fd,self.socket_fd=roles;self.image=image;self.link=link;self.ppid=link.parent_pid
        self.hand=N.M.W.packet(link.request,self.pid,self.ppid,1_000_000_000,'d'*64,link.nonce);self.messages=link.to_child
        for fd,kind in zip(roles,('inherited-image','inherited-directory','ipc')):self.fds[fd]={'kind':kind,'real':None,'data':None,'pos':0,'path':None}
        values=[str(fd) for fd in roles]
        if fault=='argv-leading-zero':values[0]='0'+values[0]
        if fault=='argv-negative':values[0]='-1'
        if fault=='argv-overflow':values[0]='2147483648'
        if fault=='argv-duplicate':values[1]=values[0]
        if fault=='argv-fd-missing':values[0]='9999'
        self.cmd=b'fx3-boot-worker\0--fds-v1\0'+b''.join(v.encode()+b'\0' for v in values)
        if fault=='argv-extra':self.cmd+=b'extra\0'
        if fault=='argv-missing-nul':self.cmd=self.cmd[:-1]
        self.exit_closed=[];self.fcntl_calls=[]

    def fd(self,*a,**kw):
        while self.next_fd in (self.image_fd,self.job_fd,self.socket_fd,198):self.next_fd+=1
        return super().fd(*a,**kw)

    def syscall(self,nr,a,b,c,d):
        if nr==56 and a==-100:
            path=T.string_at(b).decode('ascii')
            if path==f'/proc/{self.ppid}/exe' and self.ppid!=321:
                assert c==0x80000;self.exe_opens['parentexe']+=1;return self.fd('parentexe',data=self.parent,path=path)
        if nr==113:self.now=max(self.now,self.link.clock)
        if nr==80:
            if a not in self.fds:return -9
            kind=self.fds[a]['kind'];s=Kstat();special=False
            if kind in ('inherited-image','selfexe'):
                s.dev=9;s.ino=555;s.mode=0o100500;s.uid=0;s.nlink=1;s.size=len(self.image);s.mtime=1;s.ctime=2;special=True
                if kind=='inherited-image' and self.ipc_fault=='image-mismatch':s.ino+=1
                if kind=='inherited-image' and self.ipc_fault=='image-uid':s.uid=501
                if kind=='inherited-image' and self.ipc_fault=='image-mode':s.mode=0o100755
            elif kind in ('inherited-directory','ram'):
                s.dev=9;s.ino=700;s.mode=0o40700;s.uid=0;s.nlink=2;s.mtime=1;s.ctime=2;special=True
                if kind=='inherited-directory' and self.ipc_fault=='wrong-directory':s.ino+=1
            elif kind=='ipc':
                s.dev=9;s.ino=800;s.mode=0o140777;s.uid=0;s.nlink=1;special=True
            if special:T.memmove(b,T.byref(s),T.sizeof(s));return 0
        if nr==57 and a in (self.image_fd,self.job_fd,self.socket_fd):
            assert a not in self.closed;self.closed.append(a)
            if a==self.socket_fd:self.link.child_socket_closed=True
            return -5 if (a==self.image_fd and self.ipc_fault=='image-close') or (a==self.job_fd and self.ipc_fault=='directory-close') or (a==self.socket_fd and self.ipc_fault=='ipc-close') else 0
        value=super().syscall(nr,a,b,c,d)
        if nr==113:self.link.clock=max(self.link.clock,self.now)
        return value

    def fcntl(self,args):
        fd,command,arg,unused=args;self.fcntl_calls.append(dict(fd=fd,command=command))
        if fd not in (self.image_fd,self.job_fd,self.socket_fd):return -9
        assert arg==0
        if command==3:return 2 if self.ipc_fault=='image-writable' else 0x8000
        assert command==1;return 1 if self.ipc_fault=='cloexec' else 0

    def ipc(self,u,nr,args):
        if nr==73:
            with self.link.condition:
                deadline=time.monotonic()+10
                while not self.messages and not self.link.stop_wait:
                    left=deadline-time.monotonic()
                    if left<=0:raise AssertionError('same fixture channel awaits cooperative wake')
                    self.link.condition.wait(timeout=left)
                if not self.messages:self.now+=2_000_000_000
        if nr==211:
            previous=self.ipc_fault;self.ipc_fault='no-go'
            try:value=self.socket_call(u,nr,args)
            finally:self.ipc_fault=previous
            if value==320:
                hdr=bytes(u.mem_read(args[1],56));iov=struct.unpack_from('<Q',hdr,16)[0];base=struct.unpack('<Q',u.mem_read(iov,8))[0]
                raw=bytes(u.mem_read(base,320));kind=P.decode(raw)['kind'];self.link.child_packets.append(kind)
                with self.link.condition:
                    if not(kind==4 and self.link.mode=='no-done'):
                        self.link.to_parent.append(raw)
                        if kind==4 and self.link.mode=='duplicate-done':self.link.to_parent.append(raw)
                    self.link.condition.notify_all()
            return value
        return self.socket_call(u,nr,args)

    def socket_call(self,u,nr,args):
        self.ipc_calls.append(dict(number=nr,args=args))
        a,b,c,d,e,f=args
        def put(address,fmt,*values):u.mem_write(address,struct.pack(fmt,*values))
        def read(address,n):return bytes(u.mem_read(address,n))
        if nr==209:
            assert (a,b)==(self.socket_fd,1)
            if c==3:
                assert struct.unpack('<I',read(e,4))[0]==4
                put(d,'<I',1 if self.ipc_fault=='stream' else 2);put(e,'<I',4);return 0
            assert c==17 and struct.unpack('<I',read(e,4))[0]==12
            pid=self.ppid+1 if self.ipc_fault=='peer-pid' else self.ppid
            uid=501 if self.ipc_fault=='peer-uid' else 0;gid=20 if self.ipc_fault=='peer-gid' else 0
            put(d,'<III',pid,uid,gid);put(e,'<I',8 if self.ipc_fault=='peer-size' else 12);return 0
        if nr==204:
            assert a==self.socket_fd and struct.unpack('<I',read(c,4))[0]==110
            put(b,'<H',2 if self.ipc_fault=='not-unix' else 1);put(c,'<I',10 if self.ipc_fault=='named' else 2);return 0
        if nr==208:
            assert (a,b,c,e)==(self.socket_fd,1,16,4) and read(d,4)==struct.pack('<I',1)
            self.owned_mutations.append('SO_PASSCRED');return -5 if self.ipc_fault=='passcred-error' else 0
        if nr==73:
            assert b==1 and d==0 and e==8
            fd,events,revents=struct.unpack('<ihh',read(a,8));assert fd==self.socket_fd and events==1 and revents==0
            sec,ns=struct.unpack('<qq',read(c,16));assert 0<=sec<=1 and 0<=ns<1000000000
            self.polls+=1
            if self.ipc_fault=='go-block' and self.polls==2:
                self.entered.set();assert self.release.wait(timeout=10);self.now+=2_000_000_000
            if self.ipc_fault=='poll-error':return -5
            if not self.messages:return 0
            put(a+6,'<h',17 if self.ipc_fault=='poll-hup' else 1);return 1
        if nr in (211,212):
            assert a==self.socket_fd
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


class Guest(N.Guest):
    def __init__(self,raw,kernel):
        self.raw=raw;self.kernel=kernel;self.exitcode=None;self.errors=[];self.trace=[];self.slices=0
        self.u=U.Uc(U.UC_ARCH_ARM64,U.UC_MODE_ARM);self.segments=S.read_executable(raw)
        for seg in self.segments:
            flags=seg['flags'];perms=(U.UC_PROT_READ if flags&4 else 0)|(U.UC_PROT_WRITE if flags&2 else 0)|(U.UC_PROT_EXEC if flags&1 else 0)
            self.u.mem_map(seg['va'],S.align(seg['memsz'],4096),perms)
            if seg['filesz']:self.u.mem_write(seg['va'],raw[seg['offset']:seg['offset']+seg['filesz']])
        self.u.mem_map(0x70000000,0x20000,U.UC_PROT_READ|U.UC_PROT_WRITE);self.u.reg_write(A.UC_ARM64_REG_SP,0x70020000);self.u.reg_write(A.UC_ARM64_REG_CPACR_EL1,3<<20)
        self.entry=struct.unpack_from('<Q',raw,24)[0];self.u.reg_write(A.UC_ARM64_REG_PC,self.entry);self.u.hook_add(U.UC_HOOK_INTR,self.interrupt)

    def interrupt(self,u,number,unused):
        nr=u.reg_read(A.UC_ARM64_REG_X8)
        if nr not in (25,93):return super().interrupt(u,number,unused)
        try:
            assert number==2;args=[T.c_int64(u.reg_read(getattr(A,'UC_ARM64_REG_X'+str(i)))).value for i in range(4)];self.trace.append(dict(number=nr,args=args))
            if nr==25:u.reg_write(A.UC_ARM64_REG_X0,self.kernel.fcntl(args)&0xffffffffffffffff);return
            assert 0<=args[0]<=255;self.exitcode=args[0]
            # Model kernel process-exit cleanup, separately from explicit closes.
            for fd,row in self.kernel.fds.items():
                if fd not in self.kernel.closed:
                    if row['real'] is not None:os.close(row['real'])
                    self.kernel.closed.append(fd);self.kernel.exit_closed.append(fd)
                    if fd==self.kernel.socket_fd:self.kernel.link.child_socket_closed=True
            u.emu_stop()
        except BaseException as e:self.errors.append(repr(e));u.emu_stop()

    def run_worker(self):return Base.run(self)['worker_exitcode']
