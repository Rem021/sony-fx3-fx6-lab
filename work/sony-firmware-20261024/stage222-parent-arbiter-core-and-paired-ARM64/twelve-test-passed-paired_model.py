"""Two own ARM64 images exchange packets through explicit fake Linux queues.

No Linux syscall is forwarded to Mac; wait4, credentials, fork/exec and the
shared target clock are declared models. Only fixture files/O_EXCL are real.
"""
from pathlib import Path
import ctypes as T
import importlib.util,json,os,struct,sys,threading,time
H=Path(__file__).resolve().parent;R=H.parents[2];RUN=Path(sys.argv[1]);sys.argv=[sys.argv[0],str(RUN)]
OLD=H.parent/'stage221-private-IPC-entry-gate'
s=importlib.util.spec_from_file_location('worker221types_for222',OLD/'test_ipc_gate.py');N=importlib.util.module_from_spec(s);sys.modules[s.name]=N;s.loader.exec_module(N)
s=importlib.util.spec_from_file_location('parent222builder',H/'dynparent.py');D=importlib.util.module_from_spec(s);sys.modules[s.name]=D;s.loader.exec_module(D)
P=N.P;B=N.B;A=N.A;U=N.M.M.M.U
Kstat=N.M.M.M.K.M.Kstat
from fx3_recovery.files import check_volume,new_directory,read_file,encode

class Link:
    def __init__(self,request,parent_pid=321,child_pid=1234,nonce='c'*64,mode=None):
        self.request=request;self.parent_pid=parent_pid;self.child_pid=child_pid;self.nonce=nonce;self.mode=mode
        self.condition=threading.Condition();self.to_child=[];self.to_parent=[];self.stop_wait=False
        self.clock=1_000_000_000;self.finished=False;self.reaped=False;self.exit_status=0;self.child_return=None
        self.child_socket_closed=False;self.returned=threading.Event();self.exit_release=threading.Event();self.errors=[];self.thread=None
        self.child=None;self.guest=None;self.parent_packets=[];self.child_packets=[]

    def release_fixture(self):
        with self.condition:self.stop_wait=True;self.condition.notify_all()
        self.exit_release.set()
        if self.child is not None:self.child.release.set()

    def start_child(self,kernel,guest):
        self.child=kernel;self.guest=guest
        def work():
            try:
                code=guest.run_worker();self.child_return=code;self.returned.set()
                if self.mode=='hold-exit':
                    if not self.exit_release.wait(timeout=15):raise AssertionError('own fixture exit gate not released')
                self.exit_status=(22 if self.mode=='nonzero-exit' else code)<<8
            except BaseException as e:self.errors.append(repr(e));self.exit_status=99<<8;self.returned.set()
            finally:
                with self.condition:self.finished=True;self.condition.notify_all()
        self.thread=threading.Thread(target=work);self.thread.start()

class ChildKernel(N.Kernel):
    def __init__(self,name,source,profiles,busy,parent,shared,link,total=B.UNIT,fault=None):
        super().__init__(name,source,profiles,busy,parent,shared,link.request,nonce=link.nonce,fault=fault,total=total,pid=link.child_pid)
        self.link=link;self.ppid=link.parent_pid
        self.hand=N.M.W.packet(link.request,self.pid,self.ppid,1_000_000_000,'d'*64,link.nonce)
        self.messages=link.to_child

    def syscall(self,nr,a,b,c,d):
        if nr==56 and a==-100:
            path=T.string_at(b).decode('ascii')
            if path==f'/proc/{self.ppid}/exe' and self.ppid!=321:
                assert c==0x80000;self.exe_opens['parentexe']+=1;return self.fd('parentexe',data=self.parent,path=path)
        if nr==113:self.now=max(self.now,self.link.clock)
        value=super().syscall(nr,a,b,c,d)
        if nr==113:self.link.clock=max(self.link.clock,self.now)
        if nr==57 and a==198:self.link.child_socket_closed=True
        return value

    def ipc(self,u,nr,args):
        if nr==73:
            with self.link.condition:
                deadline=time.monotonic()+10
                while not self.messages and not self.link.stop_wait:
                    left=deadline-time.monotonic()
                    if left<=0:raise AssertionError('same fixture channel timed out without cooperative wake')
                    self.link.condition.wait(timeout=left)
                if not self.messages:self.now+=2_000_000_000
        if nr==211:
            old_fault=self.ipc_fault;self.ipc_fault='no-go'
            try:value=super().ipc(u,nr,args)
            finally:self.ipc_fault=old_fault
            if value==320:
                hdr=bytes(u.mem_read(args[1],56));iov=struct.unpack_from('<Q',hdr,16)[0];base=struct.unpack('<Q',u.mem_read(iov,8))[0]
                raw=bytes(u.mem_read(base,320));decoded=P.decode(raw);kind=decoded['kind'];self.link.child_packets.append(kind)
                with self.link.condition:
                    if not (kind==4 and self.link.mode=='no-done'):
                        self.link.to_parent.append(raw)
                        if kind==4 and self.link.mode=='duplicate-done':self.link.to_parent.append(raw)
                    self.link.condition.notify_all()
            return value
        return super().ipc(u,nr,args)

class ParentKernel(N.M.M.Kernel):
    def __init__(self,name,source,profiles,parent,namespace,link,fault=None):
        super().__init__(name,source,profiles,parent,parent,None)
        self.pid=link.parent_pid;self.ppid=100;self.link=link;self.namespace=Path(namespace);self.parent_fault=fault
        self.fds[199]={'kind':'parent-ipc','real':None,'data':None,'pos':0,'path':None}
        self.sent=[];self.waits=[];self.ipc_calls=[];self.injected=[];self.live_namespace_created=False

    def prepare(self,link):
        assert 199 in self.closed and self.link.finished and self.link.reaped
        self.closed.remove(199);self.link=link;link.clock=max(link.clock,self.now)
        self.fds[199]={'kind':'parent-ipc','real':None,'data':None,'pos':0,'path':None}

    def fd(self,*a,**kw):
        if self.next_fd in (198,199):self.next_fd=200
        return super().fd(*a,**kw)

    def syscall(self,nr,a,b,c,d):
        if nr==113:self.now=max(self.now,self.link.clock)
        if nr==80 and a in self.fds and self.fds[a]['kind']=='selfexe':
            s=Kstat();s.dev=1;s.ino=902;s.mode=0o100755;s.nlink=1;s.size=len(self.fds[a]['data']);s.mtime=10;s.ctime=11
            T.memmove(b,T.byref(s),T.sizeof(s));return 0
        if nr in (34,56):
            name=T.string_at(b).decode('ascii')
            if nr==34 and name=='fx3-boot-owner-session-v1':
                assert self.fds[a]['kind']=='ram' and c==0o700
                try:self.namespace.mkdir(mode=0o700);self.live_namespace_created=True;return 0
                except FileExistsError:return -17
            if nr==56 and a!=-100 and self.fds[a]['kind']=='ram' and name=='fx3-boot-owner-session-v1':
                assert c==0xb0000;return self.fd('owner',path=self.namespace)
            if nr==56 and a!=-100 and self.fds[a]['kind']=='owner':
                assert name=='owner-session.pending' and c==0xa00c1 and d==0o600
                try:real=os.open(self.namespace/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
                except FileExistsError:return -17
                return self.fd('ownerfile',real=real,path=self.namespace/name)
        if nr==80 and a in self.fds and self.fds[a]['kind'] in ('owner','ownerfile','parent-ipc'):
            row=self.fds[a];s=Kstat();s.dev=9;s.uid=0;s.nlink=1;s.ino=a
            if row['kind']=='parent-ipc':s.mode=0o140777
            else:
                actual=os.stat(row['path'],follow_symlinks=False);s.mode=actual.st_mode;s.nlink=actual.st_nlink;s.size=actual.st_size;s.ino=actual.st_ino
                s.mtime=actual.st_mtime_ns//10**9;s.mtime_ns=actual.st_mtime_ns%10**9;s.ctime=actual.st_ctime_ns//10**9;s.ctime_ns=actual.st_ctime_ns%10**9
            T.memmove(b,T.byref(s),T.sizeof(s));return 0
        if nr==64 and self.fds[a]['kind']=='ownerfile':
            raw=T.string_at(b,c);return os.write(self.fds[a]['real'],raw[:-1] if self.parent_fault=='record-short' else raw)
        if nr==82 and self.fds[a]['kind'] in ('owner','ownerfile'):
            if self.parent_fault=='record-sync':return -5
            if self.fds[a]['real'] is not None:os.fsync(self.fds[a]['real'])
            return 0
        if nr==57 and a in self.fds and self.fds[a]['kind'] in ('ownerfile','parent-ipc'):
            assert a not in self.closed;self.closed.append(a);row=self.fds[a]
            if row['real'] is not None:os.close(row['real'])
            return -5 if row['kind']=='parent-ipc' and self.parent_fault=='parent-close' else 0
        value=super().syscall(nr,a,b,c,d)
        if nr==113:self.link.clock=max(self.link.clock,self.now)
        return value

    def wait4(self,u,args):
        pid,status,options,rusage=args;assert pid==self.link.child_pid and options==1 and rusage==0
        if self.parent_fault=='foreign-child':returned=-10
        elif self.parent_fault=='wait-error':returned=-4
        elif not self.link.finished:returned=0
        elif self.link.reaped:returned=-10
        else:
            returned=pid;self.link.reaped=True;u.mem_write(status,struct.pack('<i',self.link.exit_status))
        self.waits.append(dict(pid=pid,returned=returned,child_finished=self.link.finished,status=self.link.exit_status if returned==pid else None))
        return returned

    def ipc(self,u,nr,args):
        self.ipc_calls.append(dict(number=nr,args=args));a,b,c,d,e,f=args
        def put(address,fmt,*values):u.mem_write(address,struct.pack(fmt,*values))
        def read(address,n):return bytes(u.mem_read(address,n))
        if nr==209:
            assert (a,b)==(199,1)
            if c==3:put(d,'<I',2);put(e,'<I',4);return 0
            assert c==17;put(d,'<III',self.pid,0,0);put(e,'<I',12);return 0
        if nr==204:assert a==199;put(b,'<H',1);put(c,'<I',2);return 0
        if nr==208:assert (a,b,c,e)==(199,1,16,4);return 0
        if nr==73:
            assert b==1 and d==0 and e==8 and read(c,16)==bytes(16)
            revents=(17 if self.link.child_socket_closed else 1) if self.link.to_parent else 16 if self.link.child_socket_closed else 0
            put(a+6,'<h',revents);return int(bool(revents))
        assert nr in (211,212) and a==199
        fields=struct.unpack('<QI4xQQQQI4x',read(b,56));name,namelen,iov,iovlen,control,controllen,flags=fields
        assert name==namelen==0 and iovlen==1;base,size=struct.unpack('<QQ',read(iov,16));assert size==320
        if nr==211:
            assert c==0x4040 and control==controllen==0;raw=read(base,320);decoded=P.decode(raw);kind=decoded['kind']
            assert kind in (1,3);self.sent.append(kind);self.link.parent_packets.append(kind)
            with self.link.condition:self.link.to_child.append(raw);self.link.condition.notify_all()
            return 320
        assert c==0x40000040 and controllen==256 and self.link.to_parent
        raw=self.link.to_parent.pop(0);u.mem_write(base,raw)
        credential_pid=self.link.child_pid+1 if self.parent_fault=='message-pid' else self.link.child_pid
        uid=501 if self.parent_fault=='message-uid' else 0
        ancillary=N.cmsg(2,struct.pack('<III',credential_pid,uid,0))
        if self.parent_fault=='rights':
            ancillary+=N.cmsg(1,struct.pack('<ii',360,361))
            for fd in (360,361):self.fds[fd]={'kind':'injected','real':None,'data':None,'pos':0,'path':None};self.injected.append(fd)
        u.mem_write(control,ancillary);put(b+40,'<Q',len(ancillary));put(b+48,'<I',0x40000000);return 320

class ParentGuest(N.Guest):
    def __init__(self,raw,kernel,base=0x30000000):
        self.raw=raw;self.kernel=kernel;self.base=base;self.report=D.inspect(raw);self.exitcode=None;self.errors=[];self.trace=[];self.calls=[]
        self.u=U.Uc(U.UC_ARCH_ARM64,U.UC_MODE_ARM)
        for segment in self.report['segments']:
            flags=segment['flags'];perms=(U.UC_PROT_READ if flags&4 else 0)|(U.UC_PROT_WRITE if flags&2 else 0)|(U.UC_PROT_EXEC if flags&1 else 0)
            self.u.mem_map(base+segment['va'],D.align(segment['memsz'],D.PAGE),perms)
            if segment['filesz']:self.u.mem_write(base+segment['va'],raw[segment['offset']:segment['offset']+segment['filesz']])
        for relocation in self.report['runtime_relocations']:self.u.mem_write(base+relocation['offset'],struct.pack('<Q',base+relocation['addend']))
        self.u.mem_protect(base+0x30000,D.PAGE,U.UC_PROT_READ);self.u.mem_map(0x70000000,0x20000,U.UC_PROT_READ|U.UC_PROT_WRITE);self.u.reg_write(A.UC_ARM64_REG_CPACR_EL1,3<<20)
        self.stop=0x71000000;self.u.mem_map(self.stop,4096,U.UC_PROT_READ|U.UC_PROT_EXEC)
        self.args=0x72000000;self.u.mem_map(self.args,4096,U.UC_PROT_READ|U.UC_PROT_WRITE);self.u.hook_add(U.UC_HOOK_INTR,self.interrupt)

    def interrupt(self,u,number,unused):
        if u.reg_read(A.UC_ARM64_REG_X8)!=260:return super().interrupt(u,number,unused)
        try:
            assert number==2;args=[T.c_int64(u.reg_read(getattr(A,'UC_ARM64_REG_X'+str(i)))).value for i in range(4)]
            self.trace.append(dict(number=260,args=args));value=self.kernel.wait4(u,args);u.reg_write(A.UC_ARM64_REG_X0,value&0xffffffffffffffff)
        except BaseException as e:self.errors.append(repr(e));u.emu_stop()

    def submit(self,hand,request,child):
        self.u.mem_write(self.args,hand);self.u.mem_write(self.args+512,request)
        for i,value in enumerate((self.args,self.args+512,child,199)):self.u.reg_write(getattr(A,'UC_ARM64_REG_X'+str(i)),value)
        return self.call(self.report['exports']['fx3_arbiter_submit']['va'])

    def poll(self):return self.call(self.report['exports']['fx3_arbiter_poll']['va'])
