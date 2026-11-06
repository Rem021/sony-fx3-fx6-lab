"""Own clone branches and exec transition on explicitly fake Linux, never host.
Only ordinary local fixture files are read/written; no Linux syscall forwarded.
"""
from pathlib import Path
from hashlib import sha256
import ctypes as T,importlib.util,struct,sys,os,time,zlib,threading
H=Path(__file__).resolve().parent;R=H.parents[2];RUN=Path(sys.argv[1]);sys.argv=sys.argv[:2]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
SM=module('static223_for224',H.parent/'stage223-static-worker-and-scoped-job-descriptors/static_model.py');D=module('launcher224builder',H/'dynparent.py')
M=SM.M;N=SM.N;B=SM.B;A=SM.A;U=SM.U;Kstat=SM.Kstat
from fx3_recovery.files import check_volume,read_file,encode,new_directory

def bytestring(u,address,limit=512):
 out=bytearray()
 for i in range(limit):
  x=u.mem_read(address+i,1)[0]
  if not x:return bytes(out)
  out.append(x)
 raise AssertionError('unterminated fake string')

def file_stat(row):
 s=Kstat();a=os.fstat(row['real']);s.dev=9;s.ino=a.st_ino;s.mode=a.st_mode;s.nlink=a.st_nlink;s.size=a.st_size
 s.mtime=a.st_mtime_ns//10**9;s.mtime_ns=a.st_mtime_ns%10**9;s.ctime=a.st_ctime_ns//10**9;s.ctime_ns=a.st_ctime_ns%10**9;return s

class ParentKernel(M.ParentKernel):
 def __init__(self,name,source,profiles,im,namespace,link,image,ram=None,shared=None,fault=None,total=B.UNIT):
  super().__init__(name,source,profiles,im,namespace,link)
  self.fds.pop(199);self.image=image;self.ram_path=ram or RUN/(name+'-ram');self.ram_path.mkdir(mode=0o700,exist_ok=True)
  self.shared=shared or RUN/(name+'-claims');self.launch_fault=fault;self.total=total;self.parent_socket=-1;self.child_socket=-1;self.image_fd=-1;self.root_fd=-1
  self.events=[];self.clones=[];self.stages=[];self.parent_flags_before={};self.execs=[];self.next_child=link.child_pid
  for fd in (0,1,2,900):self.fds[fd]={'kind':'unrelated','real':None,'data':None,'pos':0,'path':None,'flags':0}
 def fd(self,*args,**kw):
  fd=super().fd(*args,**kw);self.fds[fd]['flags']=1;return fd
 def prepare(self,link):
  assert self.parent_socket in self.closed and self.link.finished and self.link.reaped
  self.link=link;link.clock=max(link.clock,self.now);self.next_child=link.child_pid
 def syscall(self,nr,a,b,c,d):
  if nr==34 and T.string_at(b)==b'fx3-boot-owner-session-v1':self.events.append('reserve-session')
  if nr==56 and a!=-100 and a in self.fds and self.fds[a]['kind']=='ram':
   name=T.string_at(b).decode()
   if name=='fx3-boot-worker-223.elf':
    assert c==0xa0000;self.events.append('open-image');self.image_fd=self.fd('launch-image',data=self.image);return self.image_fd
   if name in ('fx3-boot-handoff-v1.bin','fx3-boot-request-v1.bin'):
    assert c==0xa00c2 and d==0o600;self.events.append('create-input:'+name)
    try:real=os.open(self.ram_path/name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    except FileExistsError:return -17
    return self.fd('launch-staging',real=real,path=self.ram_path/name)
  if nr==80 and a in self.fds:
   row=self.fds[a]
   if row['kind']=='launch-image':
    s=Kstat();s.dev=9;s.ino=555;s.uid=501 if self.launch_fault=='image-owner' else 0;s.nlink=1;s.mode=0o100500;s.size=len(self.image);s.mtime=1;s.ctime=2
    if self.launch_fault=='image-drift' and row['pos']:s.ctime+=1
    T.memmove(b,T.byref(s),128);return 0
   if row['kind']=='ram':
    s=Kstat();s.dev=9;s.ino=700;s.mode=0o40700;s.nlink=2;s.mtime=1;s.ctime=2;T.memmove(b,T.byref(s),128);return 0
   if row['kind']=='launch-staging':s=file_stat(row);T.memmove(b,T.byref(s),128);return 0
   if row['kind']=='parent-ipc':
    s=Kstat();s.dev=9;s.ino=800;s.mode=0o140777;s.nlink=1;T.memmove(b,T.byref(s),128);return 0
  if nr==63 and a in self.fds and self.fds[a]['kind']=='launch-image':
   row=self.fds[a];raw=row['data'][row['pos']:row['pos']+c];row['pos']+=len(raw);T.memmove(b,raw,len(raw));return len(raw)
  if nr==57 and a in self.fds and self.fds[a]['kind'] in ('launch-image','child-ipc-copy'):
   assert a not in self.closed;self.closed.append(a);return 0
  if nr==82 and a in self.fds and self.fds[a]['kind']=='launch-staging':
   if self.launch_fault=='stage-sync':return -5
   os.fsync(self.fds[a]['real']);return 0
  result=super().syscall(nr,a,b,c,d)
  if nr==56 and result>=0 and self.fds[result]['kind']=='ram':self.root_fd=result
  return result
 def special(self,u,nr,args,guest):
  a,b,c,d,e,f=args
  if nr==25:
   assert a in self.fds and a not in self.closed
   if b==3:return 2 if self.launch_fault=='image-writable' else 0x8000
   if b==1:return self.fds[a].get('flags',1)
   raise AssertionError('parent never sets borrowed FD flags')
  if nr==199:
   assert (a,b,c,e,f)==(1,0x80002,0,0,0);self.events.append('socketpair')
   if self.launch_fault=='socketpair':return -24
   self.parent_socket=self.fd('parent-ipc');self.child_socket=self.fd('child-ipc-copy');u.mem_write(d,struct.pack('<ii',self.parent_socket,self.child_socket));return 0
  if nr==68:
   assert d==0 and self.fds[a]['kind']=='launch-staging';row=self.fds[a];raw=bytes(u.mem_read(b,c));self.events.append('pwrite:'+row['path'].name)
   if self.launch_fault=='stage-short':raw=raw[:-1]
   count=os.pwrite(row['real'],raw,0);self.stages.append(dict(name=row['path'].name,count=count,sha256=sha256(raw).hexdigest()));return count
  assert nr==220 and args==[17,0,0,0,0,0];self.events.append('clone')
  if self.launch_fault=='clone':return -11
  self.parent_flags_before={fd:row.get('flags',1) for fd,row in self.fds.items() if fd not in self.closed}
  self.clones.append(dict(flags=a,child_stack=b,child_pid=self.next_child))
  k=ChildKernel(self,self.link,self.image_fd,self.root_fd,self.child_socket);g=CloneGuest(guest,k)
  self.link.start_child(k,g);return self.next_child

 def ipc(self,u,nr,args):
     self.ipc_calls.append(dict(number=nr,args=args));a,b,c,d,e,f=args
     def put(address,fmt,*values):u.mem_write(address,struct.pack(fmt,*values))
     def read(address,n):return bytes(u.mem_read(address,n))
     if nr==209:
         assert (a,b)==(self.parent_socket,1)
         if c==3:put(d,'<I',2);put(e,'<I',4);return 0
         assert c==17;put(d,'<III',self.pid,0,0);put(e,'<I',12);return 0
     if nr==204:assert a==self.parent_socket;put(b,'<H',1);put(c,'<I',2);return 0
     if nr==208:assert (a,b,c,e)==(self.parent_socket,1,16,4);return 0
     if nr==73:
         assert b==1 and d==0 and e==8 and read(c,16)==bytes(16)
         revents=(17 if self.link.child_socket_closed else 1) if self.link.to_parent else 16 if self.link.child_socket_closed else 0
         put(a+6,'<h',revents);return int(bool(revents))
     assert nr in (211,212) and a==self.parent_socket
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

class ChildKernel(SM.Kernel):
 def __init__(self,parent,link,image,root,socket):
  super().__init__(parent.namespace.name+'-spawned',parent.source,parent.profiles,parent.parent,parent.shared,link,parent.image,parent.total,roles=(image,root,socket))
  self.parent_kernel=parent;self.fds={};self.closed=[];self.next_fd=1000;self.fd_changes=[];self.exec_closed=[];self.enumerated=False
  for fd,row in parent.fds.items():
   if fd in parent.closed:continue
   self.fds[fd]=dict(row)
   if row['real'] is not None:self.fds[fd]['real']=os.dup(row['real'])
  self.fds[image]['kind']='inherited-image';self.fds[root]['kind']='inherited-directory';self.fds[socket]['kind']='ipc'
 def syscall(self,nr,a,b,c,d):
  if nr==56 and a==-100 and T.string_at(b)==b'/proc/self/fd':return self.fd('fd-enumeration')
  if nr==56 and a!=-100 and self.fds[a]['kind']=='ram':
   name=T.string_at(b).decode()
   if name in ('fx3-boot-handoff-v1.bin','fx3-boot-request-v1.bin'):
    assert c==0xa0000;self.parent_kernel.events.append('child-read:'+name)
    try:real=os.open(self.parent_kernel.ram_path/name,os.O_RDONLY|os.O_NOFOLLOW)
    except FileNotFoundError:return -2
    return self.fd('staged-reader',real=real,path=self.parent_kernel.ram_path/name)
  if nr==80 and a in self.fds and self.fds[a]['kind']=='staged-reader':s=file_stat(self.fds[a]);T.memmove(b,T.byref(s),128);return 0
  if nr==63 and self.fds[a]['kind']=='staged-reader':
   row=self.fds[a];raw=os.read(row['real'],c);row['pos']+=len(raw);T.memmove(b,raw,len(raw));return len(raw)
  if nr==57 and a in self.fds and self.fds[a]['kind']=='staged-reader':
   assert a not in self.closed;self.closed.append(a);os.close(self.fds[a]['real']);return 0
  return super().syscall(nr,a,b,c,d)
 def fcntl(self,args):
  fd,command,value,unused=args
  if fd not in self.fds or fd in self.closed:return -9
  self.fcntl_calls.append(dict(fd=fd,command=command))
  if command==3:return 0x8000
  if command==1:return self.fds[fd].get('flags',1)
  assert command==2
  if self.parent_kernel.launch_fault=='child-flags':return -5
  self.fds[fd]['flags']=value;self.fd_changes.append(dict(fd=fd,flags=value));return 0
 def special(self,u,nr,args):
  a,b,c,d,e,f=args
  if nr==61:
   assert self.fds[a]['kind']=='fd-enumeration' and c==4096
   if self.enumerated:return 0
   self.enumerated=True;data=bytearray()
   for fd in sorted(set(self.fds)-set(self.closed)):
    name=str(fd).encode()+b'\0';size=(19+len(name)+7)&-8
    data.extend(struct.pack('<QqHB',fd+1,0,size,10)+name+bytes(size-19-len(name)))
   if self.parent_kernel.launch_fault=='bad-dirent':struct.pack_into('<H',data,16,17)
   assert len(data)<=4096;u.mem_write(b,bytes(data));return len(data)
  assert nr==221 and d==e==f==0
  path=bytestring(u,a).decode();argv=[]
  for i in range(7):
   ptr=struct.unpack('<Q',u.mem_read(b+8*i,8))[0]
   if not ptr:break
   argv.append(bytestring(u,ptr))
  else:raise AssertionError('argv no terminator')
  assert struct.unpack('<Q',u.mem_read(c,8))[0]==0
  expected=[b'fx3-boot-worker',b'--fds-v1']+[str(fd).encode() for fd in (self.image_fd,self.job_fd,self.socket_fd)]
  assert path==f'/proc/self/fd/{self.image_fd}' and argv==expected
  self.parent_kernel.execs.append(dict(path=path,argv=[x.decode() for x in argv],environment_empty=True))
  self.parent_kernel.events.append('execve')
  if self.parent_kernel.launch_fault=='exec':return -13
  for fd,row in self.fds.items():
   if fd not in self.closed and row.get('flags',1)&1:
    if row['real'] is not None:os.close(row['real'])
    self.closed.append(fd);self.exec_closed.append(fd)
  live=sorted(set(self.fds)-set(self.closed));assert live==sorted([self.image_fd,self.job_fd,self.socket_fd]),live
  self.cmd=b''.join(x+b'\0' for x in argv);return None

class ParentGuest(M.ParentGuest):
 def __init__(self,raw,kernel,base=0x30000000):
  self.raw=raw;self.kernel=kernel;self.base=base;self.report=D.inspect(raw);self.exitcode=None;self.errors=[];self.trace=[];self.calls=[]
  self.u=U.Uc(U.UC_ARCH_ARM64,U.UC_MODE_ARM)
  for seg in self.report['segments']:
   flags=seg['flags'];perms=(U.UC_PROT_READ if flags&4 else 0)|(U.UC_PROT_WRITE if flags&2 else 0)|(U.UC_PROT_EXEC if flags&1 else 0)
   self.u.mem_map(base+seg['va'],D.align(seg['memsz'],D.PAGE),perms)
   if seg['filesz']:self.u.mem_write(base+seg['va'],raw[seg['offset']:seg['offset']+seg['filesz']])
  for rel in self.report['runtime_relocations']:self.u.mem_write(base+rel['offset'],struct.pack('<Q',base+rel['addend']))
  self.u.mem_protect(base+0x30000,D.PAGE,U.UC_PROT_READ);self.u.mem_map(0x70000000,0x20000,U.UC_PROT_READ|U.UC_PROT_WRITE);self.u.reg_write(A.UC_ARM64_REG_CPACR_EL1,3<<20)
  self.stop=0x71000000;self.u.mem_map(self.stop,4096,U.UC_PROT_READ|U.UC_PROT_EXEC);self.args=0x72000000;self.u.mem_map(self.args,4096,U.UC_PROT_READ|U.UC_PROT_WRITE);self.u.hook_add(U.UC_HOOK_INTR,self.interrupt)
 def interrupt(self,u,number,unused):
  nr=u.reg_read(A.UC_ARM64_REG_X8)
  if nr not in (25,68,199,220):return super().interrupt(u,number,unused)
  try:
   assert number==2;args=[T.c_int64(u.reg_read(getattr(A,'UC_ARM64_REG_X'+str(i)))).value for i in range(6)]
   self.trace.append(dict(number=nr,args=args));value=self.kernel.special(u,nr,args,self);u.reg_write(A.UC_ARM64_REG_X0,value&0xffffffffffffffff)
  except BaseException as e:self.errors.append(type(e).__name__+': '+str(e));u.emu_stop()
 def launch(self,hand,req):
  self.u.mem_write(self.args,hand);self.u.mem_write(self.args+512,req)
  for i,value in enumerate((self.args,self.args+512,0,0xffffffffffffffff)):self.u.reg_write(getattr(A,'UC_ARM64_REG_X'+str(i)),value)
  return self.call(self.report['exports']['fx3_arbiter_submit']['va'])

class CloneGuest(SM.Guest):
 def __init__(self,parent,kernel):
  self.kernel=kernel;self.errors=[];self.trace=[];self.exitcode=None;self.worker=None;self.exec_ready=False
  self.u=U.Uc(U.UC_ARCH_ARM64,U.UC_MODE_ARM)
  for start,end,perms in parent.u.mem_regions():
   self.u.mem_map(start,end-start+1,perms);self.u.mem_write(start,bytes(parent.u.mem_read(start,end-start+1)))
  regs=[getattr(A,'UC_ARM64_REG_X'+str(i)) for i in range(31)]+[A.UC_ARM64_REG_SP,A.UC_ARM64_REG_PC,A.UC_ARM64_REG_CPACR_EL1,A.UC_ARM64_REG_NZCV]
  for reg in regs:self.u.reg_write(reg,parent.u.reg_read(reg))
  self.u.reg_write(A.UC_ARM64_REG_X0,0);self.u.hook_add(U.UC_HOOK_INTR,self.interrupt)
 def interrupt(self,u,number,unused):
  nr=u.reg_read(A.UC_ARM64_REG_X8)
  if nr not in (61,221,93):return SM.Guest.interrupt(self,u,number,unused)
  try:
   assert number==2;args=[T.c_int64(u.reg_read(getattr(A,'UC_ARM64_REG_X'+str(i)))).value for i in range(6)];self.trace.append(dict(number=nr,args=args))
   if nr==93:
    self.exitcode=args[0]
    for fd,row in self.kernel.fds.items():
     if fd not in self.kernel.closed:
      if row['real'] is not None:os.close(row['real'])
      self.kernel.closed.append(fd);self.kernel.exit_closed.append(fd)
    self.kernel.link.child_socket_closed=True;u.emu_stop();return
   value=self.kernel.special(u,nr,args)
   if nr==221 and value is None:self.exec_ready=True;u.emu_stop();return
   u.reg_write(A.UC_ARM64_REG_X0,value&0xffffffffffffffff)
  except BaseException as e:self.errors.append(type(e).__name__+': '+str(e));u.emu_stop()
 def run_worker(self):
  for _ in range(500):
   if self.errors or self.exec_ready or self.exitcode is not None:break
   self.u.emu_start(self.u.reg_read(A.UC_ARM64_REG_PC),0,timeout=1_000_000,count=200_000)
  assert not self.errors,self.errors
  if self.exec_ready:
   self.worker=SM.Guest(self.kernel.image,self.kernel);code=self.worker.run_worker();self.exitcode=code;return code
  assert self.exitcode is not None,'own clone branch did not reach exec or exit';return self.exitcode
