"""Own im-context module -> own keeper -> own worker, all Linux behavior fake.
Only ordinary Mac fixture files are opened. No Sony loader/instructions run.
"""
from pathlib import Path
from hashlib import sha256
import ctypes as T,importlib.util,json,struct,sys,os,time,zlib,traceback,threading
H=Path(__file__).resolve().parent;R=H.parents[2];RUN=Path(sys.argv[1]);sys.argv=sys.argv[:2]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
K=module('keeper226_for_bootstrap227',H.parent/'stage226-static-keeper-and-parent-image-contract/keeper_model.py');D=module('bootstrap227builder',H/'dynparent.py')
L=K.L;M=K.M;SM=K.SM;N=K.N;B=K.B;P=K.P;A=K.A;U=K.U;Kstat=K.Kstat
from fx3_recovery.files import check_volume,read_file,encode,new_directory

def task(requests,keeper,worker,now=1_000_000_000):
 out=bytearray(1536);out[:16]=b'FX3BOOTPLANv1'.ljust(16,b'\0');struct.pack_into('<II',out,16,1,len(requests));out[32:48]=requests[0][16:32] if requests else b'\xbb'*16;out[48:80]=b'\xcc'*32;out[80:112]=b'\xdd'*32;out[112:144]=sha256(keeper).digest();out[144:176]=sha256(worker).digest();struct.pack_into('<IIQQ',out,176,len(keeper),len(worker),now,now+900_000_000_000)
 for i,q in enumerate(requests):out[256+i*128:384+i*128]=q
 struct.pack_into('<I',out,1532,zlib.crc32(out[:1532]));return bytes(out)

def local_stat(row):
 s=Kstat();a=os.fstat(row['real']) if row['real'] is not None else os.stat(row['path']);s.dev=9;s.ino=a.st_ino;s.mode=a.st_mode;s.nlink=a.st_nlink;s.size=a.st_size;s.mtime=a.st_mtime_ns//10**9;s.mtime_ns=a.st_mtime_ns%10**9;s.ctime=a.st_ctime_ns//10**9;s.ctime_ns=a.st_ctime_ns%10**9;return s

class BridgeKernel(L.ParentKernel):
 def __init__(self,name,source,profiles,im,keeper,worker,requests,fault=None,ram=None):
  link=M.Link(requests[0] if requests else B.request('b'*32,'boot0',0),321,7001,'c'*64)
  super().__init__(name,source,profiles,im,RUN/(name+'-lease'),link,keeper,ram=ram,fault=None)
  self.keeper=keeper;self.worker=worker;self.requests=requests;self.fault=fault;self.keepers=[];self.sent_jobs=[];self.received_results=[];self.reaper=[]
  data=task(requests,keeper,worker)
  if fault=='bad-plan':data=data[:-1]+bytes([data[-1]^1])
  if fault!='missing-plan' and not (self.ram_path/'fx3-bootstrap-plan-v1.bin').exists():(self.ram_path/'fx3-bootstrap-plan-v1.bin').write_bytes(data);os.chmod(self.ram_path/'fx3-bootstrap-plan-v1.bin',0o600)
  self.namespace=self.ram_path/'fx3-bootstrap-owner-v1';self.context_flags={}
 def fd(self,*args,**kw):
  while self.next_fd in self.fds:self.next_fd+=1
  return super().fd(*args,**kw)
 def syscall(self,nr,a,b,c,d):
  if nr==113:
   with self.link.condition:return super().syscall(nr,a,b,c,d)
  if nr in (34,56):
   name=T.string_at(b).decode()
   if nr==56 and a!=-100 and self.fds[a]['kind']=='ram':
    if name=='fx3-bootstrap-plan-v1.bin':
     assert c==0xa0000
     try:real=os.open(self.ram_path/name,os.O_RDONLY|os.O_NOFOLLOW)
     except FileNotFoundError:return -2
     return self.fd('boot-plan',real=real,path=self.ram_path/name)
    if name in ('fx3-boot-keeper-226.elf','fx3-boot-worker-226.elf'):
     assert c==0xa0000;data=self.keeper if 'keeper' in name else self.worker
     if self.fault=='image-byte' and 'keeper' in name:data=data[:65540]+bytes([data[65540]^1])+data[65541:]
     return self.fd('pin-keeper' if 'keeper' in name else 'pin-worker',data=data)
    if name=='fx3-bootstrap-owner-v1':assert c==0xb0000;return self.fd('boot-owner',path=self.namespace)
   if nr==34 and self.fds[a]['kind']=='ram' and name=='fx3-bootstrap-owner-v1':
    assert c==0o700;self.events.append('reserve-bootstrap')
    try:self.namespace.mkdir(mode=0o700);return 0
    except FileExistsError:return -17
   if nr==56 and a!=-100 and self.fds[a]['kind']=='boot-owner':
    assert name=='bootstrap.pending' and c==0xa00c1 and d==0o600
    try:real=os.open(self.namespace/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    except FileExistsError:return -17
    return self.fd('boot-record',real=real,path=self.namespace/name)
  if nr==80 and a in self.fds:
   row=self.fds[a]
   if row['kind'] in ('boot-plan','boot-owner','boot-record'):s=local_stat(row);T.memmove(b,T.byref(s),128);return 0
   if row['kind'] in ('pin-keeper','pin-worker'):
    data=row['data'];s=K.image_stat(data,900 if row['kind']=='pin-keeper' else 555);T.memmove(b,T.byref(s),128);return 0
   if row['kind']=='ram':s=Kstat();s.dev=9;s.ino=700;s.mode=0o40700;s.nlink=2;s.mtime=1;s.ctime=2;T.memmove(b,T.byref(s),128);return 0
  if nr==63 and self.fds[a]['kind'] in ('boot-plan','pin-keeper','pin-worker'):
   row=self.fds[a]
   if row['real'] is not None:raw=os.read(row['real'],c)
   else:raw=row['data'][row['pos']:row['pos']+c]
   row['pos']+=len(raw);T.memmove(b,raw,len(raw));return len(raw)
  if nr==64 and self.fds[a]['kind']=='boot-record':return os.write(self.fds[a]['real'],T.string_at(b,c))
  if nr==82 and self.fds[a]['kind'] in ('boot-owner','boot-record'):
   if self.fds[a]['real'] is not None:os.fsync(self.fds[a]['real'])
   return 0
  if nr==57 and self.fds[a]['kind'] in ('boot-plan','boot-record','boot-owner','pin-keeper','pin-worker'):
   assert a not in self.closed;self.closed.append(a)
   if self.fds[a]['real'] is not None:os.close(self.fds[a]['real'])
   return 0
  return super().syscall(nr,a,b,c,d)
 def special(self,u,nr,args,guest):
  if nr!=220:return super().special(u,nr,args,guest)
  assert args==[17,0,0,0,0,0];self.events.append('clone-keeper');self.context_flags={fd:r.get('flags',1) for fd,r in self.fds.items() if fd not in self.closed}
  self.clones.append(dict(flags=17,child_pid=7001));k=LinkedKeeper(self,self.link);g=KeeperClone(guest,k);self.keepers.append(k);self.link.start_child(k,g);return 7001
 def wait4(self,u,args):
  if self.fault=='outer-reaper' and self.link.finished and not self.link.reaped:
   self.reaper.append(dict(pid=7001,status=self.link.exit_status));self.link.reaped=True
  return super().wait4(u,args)
 def ipc(self,u,nr,args):
  a,b,c,d,e,f=args
  if nr==209:
   assert a==self.parent_socket
   if c==3:u.mem_write(d,struct.pack('<I',2));u.mem_write(e,struct.pack('<I',4));return 0
   assert c==17;u.mem_write(d,struct.pack('<III',321,0,0));u.mem_write(e,struct.pack('<I',12));return 0
  if nr==204:u.mem_write(b,struct.pack('<H',1));u.mem_write(c,struct.pack('<I',2));return 0
  if nr==208:assert a==self.parent_socket;return 0
  if nr==73:
   assert b==1 and bytes(u.mem_read(c,16))==bytes(16)
   ready=(17 if self.link.child_socket_closed else 1) if self.link.to_parent else 16 if self.link.child_socket_closed else 0;u.mem_write(a+6,struct.pack('<h',ready));return int(bool(ready))
  assert nr in (211,212) and a==self.parent_socket
  fields=struct.unpack('<QI4xQQQQI4x',u.mem_read(b,56));name,nlen,iov,ilen,control,clen,flags=fields;assert name==nlen==0 and ilen==1
  ptr,size=struct.unpack('<QQ',u.mem_read(iov,16));assert size==512
  if nr==211:
   assert c==0x4040;raw=bytes(u.mem_read(ptr,512));self.sent_jobs.append(raw)
   with self.link.condition:self.link.to_child.append(raw);self.link.condition.notify_all()
   return 512
  assert self.link.to_parent and clen==256;raw=self.link.to_parent.pop(0);self.received_results.append(P.result(raw));u.mem_write(ptr,raw);cred=N.cmsg(2,struct.pack('<III',7001,0,0));u.mem_write(control,cred);u.mem_write(b+40,struct.pack('<Q',len(cred)));u.mem_write(b+48,struct.pack('<I',0x40000000));return 512

class LinkedKeeper(K.KeeperKernel):
 def __init__(self,parent,outer):
  super().__init__(parent.namespace.parent.name+'-keeper',parent.source,parent.profiles,parent.parent,parent.keeper,parent.worker,parent.requests,fault='finish-close' if parent.fault=='keeper-close' else None)
  self.outer=outer;self.bridge=parent;self.ram_path=parent.ram_path;self.namespace=self.ram_path/(self.ram_path.name+'-keeper-owner');self.shared=self.ram_path/'fx3-boot-claims-v1';self.fds={};self.closed=[];self.next_fd=1000;self.enumerated=False
  for fd,row in parent.fds.items():
   if fd in parent.closed:continue
   self.fds[fd]=dict(row)
   if row['real'] is not None:self.fds[fd]['real']=os.dup(row['real'])
  self.role_image=next(fd for fd,row in self.fds.items() if row['kind']=='pin-keeper');self.role_root=next(fd for fd,row in self.fds.items() if row['kind']=='ram');self.role_control=parent.child_socket;self.socket_fd=self.role_control
  self.fds[self.role_image]['kind']='keeper-image';self.fds[self.role_control]['kind']='host-control';self.cmd=b''
 def syscall(self,nr,a,b,c,d):
  if nr==113:
   with self.outer.condition:
    self.now=max(self.now,self.outer.clock);self.link.clock=max(self.link.clock,self.outer.clock);value=super().syscall(nr,a,b,c,d);self.outer.clock=max(self.outer.clock,self.now,self.link.clock);return value
  if nr==56 and a==-100 and T.string_at(b)==b'/proc/self/fd':return self.fd('fd-enumeration')
  value=super().syscall(nr,a,b,c,d)
  if nr==57 and a==self.role_control:
   self.outer.child_socket_closed=True
   if self.fault=='finish-close':return -5
  return value
 def fcntl(self,args):
  fd,command,value,unused=args
  if fd not in self.fds or fd in self.closed:return -9
  if command==3:return 0x8000
  if command==1:return self.fds[fd].get('flags',1)
  assert command==2;self.fds[fd]['flags']=value;return 0
 def special(self,u,nr,args,guest=None):
  a,b,c,d,e,f=args
  if nr==220:
   assert args==[17,0,0,0,0,0];self.events.append('clone');self.parent_flags_before={fd:r.get('flags',1) for fd,r in self.fds.items() if fd not in self.closed};self.clones.append(dict(flags=17,child_stack=0,child_pid=self.next_child))
   k=LinkedWorker(self,self.link,self.image_fd,self.root_fd,self.child_socket);g=L.CloneGuest(guest,k);self.links.append(self.link);self.link.start_child(k,g);return self.next_child
  if nr==25:return self.fcntl(args[:4])
  if nr==61:
   assert self.fds[a]['kind']=='fd-enumeration'
   if self.enumerated:return 0
   self.enumerated=True;raw=bytearray()
   for fd in sorted(set(self.fds)-set(self.closed)):
    name=str(fd).encode()+b'\0';size=(19+len(name)+7)&-8;raw.extend(struct.pack('<QqHB',fd+1,0,size,10)+name+bytes(size-19-len(name)))
   u.mem_write(b,bytes(raw));return len(raw)
  if nr==221:
   argv=[]
   for i in range(7):
    ptr=struct.unpack('<Q',u.mem_read(b+8*i,8))[0]
    if not ptr:break
    argv.append(L.bytestring(u,ptr))
   expected=[b'fx3-boot-keeper',b'--fds-v1']+[str(fd).encode() for fd in (self.role_image,self.role_root,self.role_control)]
   assert argv==expected and L.bytestring(u,a)==f'/proc/self/fd/{self.role_image}'.encode() and struct.unpack('<Q',u.mem_read(c,8))[0]==0
   for fd,row in self.fds.items():
    if fd not in self.closed and row.get('flags',1)&1:
     if row['real'] is not None:os.close(row['real'])
     self.closed.append(fd)
   assert sorted(set(self.fds)-set(self.closed))==sorted([self.role_image,self.role_root,self.role_control]);self.cmd=b''.join(x+b'\0' for x in argv);return None
  return super().special(u,nr,args,guest)
 def ipc(self,u,nr,args):
  a,b,c,d,e,f=args;is_host=(nr==73 and struct.unpack('<i',u.mem_read(a,4))[0]==self.role_control) or (nr!=73 and a==self.role_control)
  if not is_host:return self.worker_ipc(u,nr,args)
  if nr==209:
   if c==3:u.mem_write(d,struct.pack('<I',2));u.mem_write(e,struct.pack('<I',4));return 0
   u.mem_write(d,struct.pack('<III',321,0,0));u.mem_write(e,struct.pack('<I',12));return 0
  if nr==204:u.mem_write(b,struct.pack('<H',1));u.mem_write(c,struct.pack('<I',2));return 0
  if nr==208:return 0
  if nr==73:
   with self.outer.condition:
    until=time.monotonic()+20
    while not self.outer.to_child and time.monotonic()<until:self.outer.condition.wait(timeout=max(.001,until-time.monotonic()))
   if not self.outer.to_child:return 0
   u.mem_write(a+6,struct.pack('<h',1));return 1
  assert nr in (211,212);name,nlen,iov,ilen,control,clen,flags=struct.unpack('<QI4xQQQQI4x',u.mem_read(b,56));ptr,size=struct.unpack('<QQ',u.mem_read(iov,16));assert size==512
  if nr==211:
   raw=bytes(u.mem_read(ptr,512));self.host_results.append(P.result(raw))
   with self.outer.condition:self.outer.to_parent.append(raw);self.outer.condition.notify_all()
   return 512
  raw=self.outer.to_child.pop(0);self.host_jobs.append(raw)
  if struct.unpack_from('<I',raw,20)[0]==1:
   req=raw[288:416];nonce=raw[64:96].hex();link=M.Link(req,7001,9001+len(self.links),nonce);link.clock=max(self.now,self.outer.clock)
   if self.started:self.prepare(link)
   else:self.link=link;self.next_child=link.child_pid;self.started=True
   self.current_job=raw
  u.mem_write(ptr,raw);cred=N.cmsg(2,struct.pack('<III',321,0,0));u.mem_write(control,cred);u.mem_write(b+40,struct.pack('<Q',len(cred)));u.mem_write(b+48,struct.pack('<I',0x40000000));return 512

class LinkedWorker(K.WorkerKernel):
 def __init__(self,*args):
  super().__init__(*args);self.next_fd=max(self.fds)+1
 def syscall(self,nr,a,b,c,d):
  if nr==113:
   outer=self.parent_kernel.outer
   with outer.condition:
    self.now=max(self.now,outer.clock);self.link.clock=max(self.link.clock,outer.clock);v=super().syscall(nr,a,b,c,d);outer.clock=max(outer.clock,self.now,self.link.clock);return v
  return super().syscall(nr,a,b,c,d)

class KeeperClone(L.CloneGuest):
 def run_worker(self):
  for _ in range(500):
   if self.errors or self.exec_ready or self.exitcode is not None:break
   self.u.emu_start(self.u.reg_read(A.UC_ARM64_REG_PC),0,timeout=1_000_000,count=200_000)
  assert not self.errors,self.errors
  if self.exec_ready:
   self.worker=K.KeeperGuest(self.kernel.keeper,self.kernel);code=self.worker.run_keeper();self.exitcode=code;return code
  assert self.exitcode is not None;return self.exitcode

class BridgeGuest(L.ParentGuest):
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
  except BaseException as e:self.errors.append(traceback.format_exc());u.emu_stop()
 def step(self,poison=0xdeadbeefcafebabe):
  for i in range(8):self.u.reg_write(getattr(A,'UC_ARM64_REG_X'+str(i)),(poison+i)&0xffffffffffffffff)
  return self.call(self.report['exports']['fx3_bootstrap_step']['va'])
 def status(self):return self.call(self.report['exports']['fx3_bootstrap_status']['va'])
