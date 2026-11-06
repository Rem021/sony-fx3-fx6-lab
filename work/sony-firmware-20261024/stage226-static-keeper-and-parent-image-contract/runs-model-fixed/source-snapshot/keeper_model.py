"""Own standalone keeper and worker. Every Linux call/process/credential is fake.
Mac ordinary fixture files only. Original im is hash data, never executable.
"""
from pathlib import Path
from hashlib import sha256
import ctypes as T,importlib.util,struct,sys,os,time,zlib,traceback
H=Path(__file__).resolve().parent;R=H.parents[2];RUN=Path(sys.argv[1]);sys.argv=sys.argv[:2]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
L=module('launch224_for_keeper226',H.parent/'stage224-controlled-launcher-and-preexec-image-pin/launch_model.py')
P=module('protocol226',H/'protocol.py');WK=module('worker226builder',H/'worker/static_build.py');KK=module('keeper226builder',H/'keeper/static_build.py')
M=L.M;SM=L.SM;N=L.N;B=L.B;A=L.A;U=L.U;Kstat=L.Kstat
from fx3_recovery.files import check_volume,read_file,new_directory,encode

def image_stat(data,ino):
 s=Kstat();s.dev=9;s.ino=ino;s.mode=0o100500;s.nlink=1;s.size=len(data);s.mtime=1;s.ctime=2;return s

class KeeperKernel(L.ParentKernel):
 def __init__(self,name,source,profiles,im,keeper,worker,requests,fault=None):
  link=M.Link(requests[0] if requests else B.request('b'*32,'boot0',0),7001,9001,'c'*64)
  super().__init__(name,source,profiles,im,RUN/(name+'-owner'),link,worker,fault=None,total=B.MAX_BOOT if requests and len(requests)>1 else B.UNIT)
  for fd in (0,1,2,900):self.fds.pop(fd)
  self.pid=7001;self.ppid=321;self.keeper=keeper;self.worker=worker;self.fault=fault;self.requests=requests;self.job_index=0;self.current_job=None;self.host_jobs=[];self.host_results=[];self.links=[]
  self.role_image=71;self.role_root=72;self.role_control=73
  for fd,kind,data in [(71,'keeper-image',keeper),(72,'ram',None),(73,'host-control',None)]:self.fds[fd]={'kind':kind,'real':None,'data':data,'pos':0,'path':None,'flags':0}
  self.cmd=b'fx3-boot-keeper\0--fds-v1\0'+b'71\0'+b'72\0'+b'73\0'
  self.socket_fd=73;self.exit_closed=[]
  self.own_action=struct.pack('<QQQQ',1,2,0,0) # inherited IGN/NOCLDWAIT to be cleared only in keeper
  self.im_action=0x402f4c;self.signal_ops=[];self.im_reaper_attempts=[];self.started=False
 def fd(self,*a,**kw):
  while self.next_fd in self.fds:self.next_fd+=1
  return super().fd(*a,**kw)
 def syscall(self,nr,a,b,c,d):
  if nr==56:
   name=T.string_at(b).decode()
   if a==-100 and name=='/proc/self/exe':return self.fd('keeper-exe',data=self.keeper)
   if a==-100 and name=='/proc/self/cmdline':return self.fd('cmd',data=self.cmd)
   if a==-100 and name=='/proc/321/exe':return self.fd('parentexe',data=self.parent)
   if a!=-100 and self.fds[a]['kind']=='ram' and name=='fx3-boot-worker-226.elf':
    assert c==0xa0000;self.events.append('open-image');self.image_fd=self.fd('launch-image',data=self.worker);return self.image_fd
   if a!=-100 and self.fds[a]['kind']=='ram' and name=='fx3-boot-handoff-v2.bin':
    assert c==0xa00c2 and d==0o600;self.events.append('create-input:'+name)
    try:real=os.open(self.ram_path/name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    except FileExistsError:return -17
    return self.fd('launch-staging',real=real,path=self.ram_path/name)
  if nr==80 and a in self.fds:
   row=self.fds[a]
   if row['kind'] in ('keeper-image','keeper-exe'):
    s=image_stat(self.keeper,900);T.memmove(b,T.byref(s),128);return 0
   if row['kind']=='host-control':
    s=Kstat();s.dev=9;s.ino=901;s.mode=0o140777;s.nlink=1;T.memmove(b,T.byref(s),128);return 0
  if nr==63 and self.fds[a]['kind'] in ('keeper-exe','keeper-image'):
   row=self.fds[a];raw=row['data'][row['pos']:row['pos']+c];row['pos']+=len(raw);T.memmove(b,raw,len(raw));return len(raw)
  if nr==57 and self.fds[a]['kind'] in ('keeper-image','keeper-exe','host-control'):
   assert a not in self.closed;self.closed.append(a);return -5 if self.fault=='finish-close' and a==73 else 0
  return super().syscall(nr,a,b,c,d)
 def special(self,u,nr,args,guest):
  a,b,c,d,e,f=args
  if nr==134:
   assert a==17 and d==8;self.signal_ops.append(dict(pid=self.pid,set=bool(b),query=bool(c)))
   if self.fault=='signal-error':return -22
   if b:
    raw=bytes(u.mem_read(b,32));assert raw==bytes(32);self.own_action=raw
   if c:
    raw=struct.pack('<QQQQ',1,2,0,0) if self.fault=='signal-query' else self.own_action;u.mem_write(c,raw)
   return 0
  if nr==101:
   assert struct.unpack('<qq',u.mem_read(a,16))==(0,20000000) and b==0
   time.sleep(.005);self.now+=20_000_000;self.link.clock=max(self.link.clock,self.now);return 0
  if nr==25 and a in (71,72,73):
   if b==3:return 0x8000
   assert b==1;return self.fds[a]['flags']
  if nr!=220:return super().special(u,nr,args,guest)
  assert args==[17,0,0,0,0,0];self.events.append('clone');self.parent_flags_before={fd:row.get('flags',1) for fd,row in self.fds.items() if fd not in self.closed}
  self.clones.append(dict(flags=17,child_stack=0,child_pid=self.next_child))
  k=WorkerKernel(self,self.link,self.image_fd,self.root_fd,self.child_socket);g=L.CloneGuest(guest,k);self.links.append(self.link);self.link.start_child(k,g);return self.next_child
 def wait4(self,u,args):
  if self.link.finished and not self.link.reaped:
   eligible=self.link.child is not None and self.link.child.ppid==321
   self.im_reaper_attempts.append(dict(im_pid=321,worker_ppid=self.link.child.ppid if self.link.child else None,eligible=eligible))
   assert not eligible and self.im_action==0x402f4c and self.own_action==bytes(32)
  return super().wait4(u,args)
 def host_next(self):
  if self.job_index<len(self.requests):
   req=self.requests[self.job_index];nonce=format(self.job_index+1,'x')*64
   raw=P.job(req,self.job_index+1,self.pid,max(self.now,self.link.clock),sha256(self.keeper).hexdigest(),len(self.keeper),sha256(self.worker).hexdigest(),nonce)
   link=M.Link(req,self.pid,9001+self.job_index,nonce)
   if self.started:self.prepare(link)
   else:self.link=link;self.next_child=link.child_pid;self.started=True
   self.current_job=raw
  else:raw=P.job(b'',self.job_index+1,self.pid,max(self.now,self.link.clock),sha256(self.keeper).hexdigest(),len(self.keeper),sha256(self.worker).hexdigest(),finish=True)
  if self.fault=='job-keeper-hash' and self.job_index==0:
   x=bytearray(raw);x[416]^=1;struct.pack_into('<I',x,508,zlib.crc32(x[:508]));raw=bytes(x)
  self.host_jobs.append(raw);self.job_index+=1;return raw
 def ipc(self,u,nr,args):
  a,b,c,d,e,f=args
  if nr==73:
   fd=struct.unpack('<i',u.mem_read(a,4))[0]
   if fd!=73:return self.worker_ipc(u,nr,args)
   assert b==1 and struct.unpack('<qq',u.mem_read(c,16))==(1,0);u.mem_write(a+6,struct.pack('<h',1));return 1
  if a!=73:return self.worker_ipc(u,nr,args)
  if nr==209:
   if c==3:u.mem_write(d,struct.pack('<I',2));u.mem_write(e,struct.pack('<I',4));return 0
   assert c==17;u.mem_write(d,struct.pack('<III',321,0,0));u.mem_write(e,struct.pack('<I',12));return 0
  if nr==204:u.mem_write(b,struct.pack('<H',1));u.mem_write(c,struct.pack('<I',2));return 0
  if nr==208:assert (b,c,e)==(1,16,4);return 0
  assert nr in (211,212);fields=struct.unpack('<QI4xQQQQI4x',u.mem_read(b,56));name,nlen,iov,ilen,control,clen,flags=fields;assert name==nlen==0 and ilen==1
  ptr,size=struct.unpack('<QQ',u.mem_read(iov,16));assert size==512
  if nr==211:
   raw=bytes(u.mem_read(ptr,512));dec=P.result(raw);assert dec['job_sha256']==sha256(self.host_jobs[-1]).hexdigest();self.host_results.append(dec);return 512
  assert clen==256;raw=self.host_next();u.mem_write(ptr,raw)
  cred=L.N.cmsg(2,struct.pack('<III',322 if self.fault=='host-credentials' else 321,0,0));u.mem_write(control,cred);u.mem_write(b+40,struct.pack('<Q',len(cred)));u.mem_write(b+48,struct.pack('<I',0x40000000));return 512
 def worker_ipc(self,u,nr,args):
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
         assert kind in (1,3);self.sent.append(kind);self.link.parent_packets.append(kind);self.events.append('send:'+str(kind))
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


class WorkerKernel(L.ChildKernel):
 def __init__(self,parent,link,image,root,socket):
  super().__init__(parent,link,image,root,socket);self.parent_image_fd=parent.role_image;self.fds[self.parent_image_fd]['kind']='parent-image-v2';self.parent=parent.keeper
  self.hand=bytearray(parent.current_job[32:288]);struct.pack_into('<I',self.hand,128,link.child_pid);struct.pack_into('<I',self.hand,252,zlib.crc32(self.hand[:252]));self.hand=bytes(self.hand)
  if parent.fault=='worker-parent-data':self.parent=bytes([self.parent[0]^1])+self.parent[1:]
 def syscall(self,nr,a,b,c,d):
  if nr==56:
   name=T.string_at(b).decode()
   if a==-100 and name==f'/proc/{self.ppid}/exe':return self.fd('keeper-parent-exe',data=self.parent)
   if a!=-100 and self.fds[a]['kind']=='ram' and name=='fx3-boot-handoff-v2.bin':
    assert c==0xa0000;real=os.open(self.parent_kernel.ram_path/name,os.O_RDONLY|os.O_NOFOLLOW);return self.fd('staged-reader',real=real,path=self.parent_kernel.ram_path/name)
  if nr==80 and a in self.fds and self.fds[a]['kind'] in ('parent-image-v2','keeper-parent-exe'):
   s=image_stat(self.parent_kernel.keeper,900);T.memmove(b,T.byref(s),128);return 0
  if nr==63 and self.fds[a]['kind']=='keeper-parent-exe':
   row=self.fds[a];raw=row['data'][row['pos']:row['pos']+c];row['pos']+=len(raw);T.memmove(b,raw,len(raw));return len(raw)
  if nr==57 and self.fds[a]['kind'] in ('parent-image-v2','keeper-parent-exe'):
   assert a not in self.closed;self.closed.append(a);return 0
  return super().syscall(nr,a,b,c,d)
 def special(self,u,nr,args):
  a,b,c,d,e,f=args
  if nr!=221:return super().special(u,nr,args)
  argv=[]
  for i in range(8):
   ptr=struct.unpack('<Q',u.mem_read(b+8*i,8))[0]
   if not ptr:break
   argv.append(L.bytestring(u,ptr))
  else:raise AssertionError('unterminated v2 argv')
  expected=[b'fx3-boot-worker',b'--fds-v2']+[str(fd).encode() for fd in (self.image_fd,self.job_fd,self.socket_fd,self.parent_image_fd)]
  assert argv==expected and L.bytestring(u,a)==f'/proc/self/fd/{self.image_fd}'.encode() and struct.unpack('<Q',u.mem_read(c,8))[0]==0
  for fd,row in self.fds.items():
   if fd not in self.closed and row.get('flags',1)&1:
    if row['real'] is not None:os.close(row['real'])
    self.closed.append(fd);self.exec_closed.append(fd)
  live=sorted(set(self.fds)-set(self.closed));assert live==sorted([self.image_fd,self.job_fd,self.socket_fd,self.parent_image_fd]),live
  self.parent_kernel.execs.append(dict(argv=[x.decode() for x in argv],live_FDs=live,environment_empty=True))
  self.cmd=b''.join(x+b'\0' for x in argv);return None

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

class KeeperGuest(SM.Guest):
 def interrupt(self,u,number,unused):
  nr=u.reg_read(A.UC_ARM64_REG_X8)
  if nr not in (25,68,73,134,199,204,208,209,211,212,220,260,101):return super().interrupt(u,number,unused)
  try:
   assert number==2;args=[T.c_int64(u.reg_read(getattr(A,'UC_ARM64_REG_X'+str(i)))).value for i in range(6)];self.trace.append(dict(number=nr,args=args))
   if nr==260:value=self.kernel.wait4(u,args[:4])
   elif nr in (73,204,208,209,211,212):value=self.kernel.ipc(u,nr,args)
   else:value=self.kernel.special(u,nr,args,self)
   u.reg_write(A.UC_ARM64_REG_X0,value&0xffffffffffffffff)
  except BaseException:self.errors.append(traceback.format_exc());u.emu_stop()
 def run_keeper(self):return SM.Base.run(self)['worker_exitcode']
