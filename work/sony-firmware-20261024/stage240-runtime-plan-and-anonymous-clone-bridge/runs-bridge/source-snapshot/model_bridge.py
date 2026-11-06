"""Execute OWN capsule only. All Linux/IPC/proc/signal behavior is modeled.
Actual clone calls create the two modeled processes; none are pre-created.
"""
from pathlib import Path
from hashlib import sha256
from collections import deque
import importlib.util,json,struct,sys,traceback,zlib
import bridge_build as D
import unicorn as U
import unicorn.arm64_const as A
H=Path(__file__).resolve().parent;B=H.parent
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=sys.modules.get('isolated_build');sys.modules['isolated_build']=module('builder237_bridge',B/'stage237-isolated-collector-child-domain/isolated_build.py')
try:M=module('kernel237_bridge',B/'stage237-isolated-collector-child-domain/model_collector.py')
finally:
 if old is None:sys.modules.pop('isolated_build',None)
 else:sys.modules['isolated_build']=old
REG=[getattr(A,'UC_ARM64_REG_X'+str(n)) for n in range(6)]
BLOCKED=((1<<64)-1)&~((1<<8)|(1<<18));PLAN_AT=0x72000000
def plan(raw,issued=1_000_000_000,expires=61_000_000_000,nonce=b'\xbb'*16):
 p=bytearray(256);p[:16]=b'FX3ENTRYPLANv1'.ljust(16,b'\0');struct.pack_into('<III',p,16,1,1,1);p[32:48]=nonce;p[48:80]=b'\xcc'*32;p[80:112]=b'\xdd'*32;p[112:144]=sha256(raw).digest();struct.pack_into('<QQI',p,144,issued,expires,1);struct.pack_into('<I',p,252,zlib.crc32(p[:252]));return bytes(p)
def proc_stat(p):
 v={n:'0' for n in range(4,53)};v.update({4:str(p.parent),20:str(p.threads),22:str(p.start_tick),52:str(p.status or 0),8:'-1',18:'20'})
 return f'{p.pid} (own {p.role}) {"S" if p.alive else "Z"} '.encode()+(' '.join(v[n] for n in range(4,53))+'\n').encode()
class Process(M.Process):
 def __init__(self,pid,parent,role):super().__init__(pid,parent,role);self.start_tick=100;self.exit_signal=17;self.mappings=[]
 def fd(self,d):
  n=0
  while n in self.fds:n+=1
  self.fds[n]=d;return n
class Kernel(M.Kernel):
 def __init__(self,raw,job=None,fault=None,pid=321,tid=777,child_pid=5001,worker_pid=7002,clock=1_000_000_000):
  super().__init__(raw,None);self.fault=fault;self.clock=clock;self.root=Process(pid,1,'caller');self.root.tid=tid;self.root.mask=0x400
  for fd in [0,1,2,7,9]:self.root.fds[fd]=dict(kind='borrowed',name=str(fd),cloexec=fd&1)
  self.host=self.root;self.host_before=dict(self.root.fds);self.borrowed=dict(self.root.fds);self.collector=None;self.worker=None;self.processes={pid:self.root};self.root_result=None;self.job=job or plan(raw,clock,clock+60_000_000_000);self.initial_plan_sha=sha256(self.job).hexdigest();self.child_pid=child_pid;self.worker_pid=worker_pid;self.clone_events=[];self.mask_events=[];self.mapping_events=[];self.messages=[];self.received=[];self.reaper_events=[];self.root_sleeps=0;self.copied_base=None;self.after_root_FDs=None;self.original_base=None;self.drop_old=True
  if fault=='baseline-SIGCHLD-blocked':self.root.mask|=1<<16
  self.original_mask=self.root.mask
 def clone(self,g,args):
  p=g.p;outer=p is self.root;assert args==([17,0,0,0,0,0] if outer else [0]*6)
  assert p.mask==BLOCKED and (outer or p is self.collector)
  if self.fault=='outer-clone-error' and outer:return -11
  pid=self.child_pid if outer else self.worker_pid;child=Process(pid,p.pid,'collector' if outer else 'worker');child.exit_signal=17 if outer else 0;child.start_tick=max(1,self.clock//10_000_000);child.mask=p.mask;child.actions=dict(p.actions);child.fds=dict(p.fds);child.mappings=list(p.mappings)
  cg=Guest(self,child,copy_from=g);cg.u.reg_write(A.UC_ARM64_REG_X0,0);self.processes[pid]=child
  if outer:
   self.collector=child;assert self.copied_base+D.PAGE<=cg.u.reg_read(A.UC_ARM64_REG_PC)<self.copied_base+2*D.PAGE
   if self.drop_old:cg.drop_original()
   if self.fault=='mutate-input-after-clone':g.u.mem_write(PLAN_AT+32,b'\x19')
  else:self.worker=child
  self.clone_events.append(dict(parent=p.pid,child=pid,role=child.role,flags=args[0],parent_mask=p.mask,private_VM_files_sighand=True,resume_pc=cg.u.reg_read(A.UC_ARM64_REG_PC),old_file_image_removed_before_first_child_instruction=outer and self.drop_old));return pid
 def reap(self,reason):
  p=self.collector
  if not p or p.alive or p.reaped or p.exit_signal!=17:return
  p.reaped=True;self.reaper_events.append(dict(reason=reason,pid=p.pid,status=p.status,only_fake_Sony_reaper_semantics=True))
 def run_child(self):
  p=self.collector
  if p and p.alive:p.guest.paused=False;p.guest.run()
 def syscall(self,g,n,args):
  p=g.p;u=g.u;a,b,c,d,e,f=args;self.syscalls.append((p.role,n))
  def text(at):
   v=bytearray()
   for i in range(256):
    x=u.mem_read(at+i,1)[0]
    if not x:return v.decode('ascii')
    v.append(x)
   raise AssertionError('unterminated string')
  if n in (172,173,178):return p.pid if n==172 else p.parent if n==173 else p.tid
  if n in (174,175):return 501 if self.fault=='not-root' else 0
  if n==113:
   self.clock+=1000
   if self.fault=='expire-after-copy' and self.mapping_events:self.clock=struct.unpack_from('<Q',self.job,152)[0]
   u.mem_write(b,struct.pack('<qq',self.clock//10**9,self.clock%10**9));return 0
  if n==135:
   assert p is self.root or p is self.collector;assert a==2 and d==8
   if b:
    value=struct.unpack('<Q',u.mem_read(b,8))[0]
    if p is self.root and value==self.original_mask and self.fault=='mask-restore-error':return -1
    old=p.mask;p.mask=value
    if c:u.mem_write(c,struct.pack('<Q',old))
    self.mask_events.append(dict(role=p.role,before=old,after=value))
    if p is self.root and not value&(1<<16) and self.fault!='no-parent-reap':self.reap('saved parent mask restored after sentinel or cleanup')
   elif c:u.mem_write(c,struct.pack('<Q',p.mask))
   return 0
  if n==134:
   assert p is self.collector and a not in (9,19) and d==8
   if b:p.actions[a]=bytes(u.mem_read(b,32))
   if c:u.mem_write(c,p.actions.get(a,bytes(32)))
   return 0
  if n==167:assert a==37;u.mem_write(b,struct.pack('<i',int(p.subreaper)));return 0
  if n==56:
   path=text(b)
   if path=='/proc/self':return p.fd(dict(kind='procdir',object=p,inode=7000+p.pid,cloexec=1))
   if path=='/proc/self/status':return p.fd(dict(kind='status',data=f'Pid:\t{p.pid}\nTgid:\t{p.pid}\nPPid:\t{p.parent}\nThreads:\t{p.threads}\nTracerPid:\t{p.tracer}\n'.encode(),pos=0))
   if path=='/proc/self/fd':return p.fd(dict(kind='scan',entries=None,pos=0))
   if path=='stat' and a in p.fds and p.fds[a]['kind']=='procdir':
    obj=p.fds[a]['object']
    if obj.reaped:return -2
    return p.fd(dict(kind='stat',object=obj,data=None,pos=0,inode=8000+p.pid))
   self.source_accesses.append(path);raise AssertionError('unexpected source path '+path)
  if n==63:
   row=p.fds[a]
   if row['kind']=='stat' and row['data'] is None:
    if row['object'].reaped:return -3
    row['data']=proc_stat(row['object'])
   assert row['kind'] in ('stat','status');data=row['data'][row['pos']:row['pos']+c];row['pos']+=len(data);u.mem_write(b,data);return len(data)
  if n==80:
   row=p.fds[a];mode=0o40500 if row['kind']=='procdir' else 0o140600 if row['kind']=='socket' else 0o100444;v=bytearray(128);struct.pack_into('<QQIIII',v,0,9,row.get('inode',9000+a),mode,1,0,0);u.mem_write(b,bytes(v));return 0
  if n==44:u.mem_write(b,struct.pack('<15Q',0x9fa0,*([0]*14)));return 0
  if n==25:assert b==1;return p.fds[a].get('cloexec',0)
  if n==61:
   row=p.fds[a];assert row['kind']=='scan'
   if row['entries'] is None:row['entries']=['.','..']+[str(fd) for fd in sorted(p.fds)]
   out=bytearray()
   while row['pos']<len(row['entries']):
    name=row['entries'][row['pos']].encode()+b'\0';length=(19+len(name)+7)&~7
    if len(out)+length>c:break
    out+=struct.pack('<QqHB',1,row['pos']+1,length,0)+name+bytes(length-19-len(name));row['pos']+=1
   u.mem_write(b,bytes(out));return len(out)
  if n==57:
   assert a in p.fds,(p.role,a,sorted(p.fds));row=p.fds.pop(a);self.closes.append(dict(role=p.role,fd=a,kind=row['kind']))
   if p is self.worker and row['kind']=='socket' and self.fault=='worker-close-error':return -5
   return 0
  if n==199:
   assert (a,b,c)==(1,0x80002,0);left=dict(kind='socket',queue=deque(),creator=p.pid,cloexec=1);right=dict(kind='socket',queue=deque(),creator=p.pid,cloexec=1);left['peer']=right;right['peer']=left
   x=p.fd(left);y=p.fd(right);u.mem_write(d,struct.pack('<ii',x,y));return 0
  if n==208:assert (b,c,e)==(1,16,4);p.fds[a]['passcred']=True;return 0
  if n==209:
   row=p.fds[a];assert row['kind']=='socket' and b==1
   if c in (3,16):u.mem_write(d,struct.pack('<I',2 if c==3 else int(row.get('passcred',False))));u.mem_write(e,struct.pack('<I',4));return 0
   if c==17:u.mem_write(d,struct.pack('<III',row['creator'],0,0));u.mem_write(e,struct.pack('<I',12));return 0
   raise AssertionError(('getsockopt',c))
  if n==204:u.mem_write(b,struct.pack('<H',1));u.mem_write(c,struct.pack('<I',2));return 0
  if n in (211,212):
   row=p.fds[a];assert row['kind']=='socket';_,_,iov,ilen,control,capacity,_=struct.unpack('<QI4xQQQQI4x',u.mem_read(b,56));ptr,size=struct.unpack('<QQ',u.mem_read(iov,16));assert ilen==1 and size==256
   if n==211:
    data=bytes(u.mem_read(ptr,size));fds=[]
    if control:
     assert capacity==24 and struct.unpack('<QII',u.mem_read(control,16))==(20,1,1);fd=struct.unpack('<I',u.mem_read(control+16,4))[0];fds=[dict(p.fds[fd])];assert fds[0]['object'] is p
    typ=struct.unpack_from('<I',data,20)[0];self.messages.append(dict(sender=p.pid,role=p.role,type=typ,plan_sha=data[56:88].hex(),image_sha=data[88:120].hex(),issued=struct.unpack_from('<Q',data,120)[0],expires=struct.unpack_from('<Q',data,128)[0],payload_sha256=sha256(data).hexdigest()))
    if self.fault=='bad-HELLO' and typ==3:data=data[:40]+bytes([data[40]^1])+data[41:]
    row['peer']['queue'].append((data,p.pid,fds));return size
   assert c&64 and c&0x40000000
   if not row['queue']:return -11
   data,sender,fds=row['queue'].popleft();ctl=M.cmsg(2,struct.pack('<III',sender,0,0))
   if fds:
    got=[]
    for desc in fds:desc['cloexec']=1;fd=p.fd(desc);got.append(fd);self.received.append(dict(receiver=p.pid,fd=fd,object_pid=desc['object'].pid))
    ctl+=M.cmsg(1,b''.join(struct.pack('<I',fd) for fd in got))
   assert len(ctl)<=capacity;u.mem_write(ptr,data);u.mem_write(control,ctl);u.mem_write(b+40,struct.pack('<Q',len(ctl)));u.mem_write(b+48,bytes(4));return len(data)
  if n==222:
   assert p is self.root and (a,c,d,e,f)==(0,3,0x22,-1,0) and b==5*D.PAGE
   if self.fault=='mmap-error':return -12
   raw=0x50001000;u.mem_map(raw,b,U.UC_PROT_READ|U.UC_PROT_WRITE);p.mappings.append((raw,b));self.copied_base=(raw+D.PAGE-1)&-D.PAGE;self.mapping_events.append(dict(event='anonymous_RW',raw=raw,bytes=b,aligned=self.copied_base));return raw
  if n==226:
   assert p is self.root and not(c&2 and c&4)
   if self.fault=='executable-protection-error' and c&4:return -13
   u.mem_protect(a,b,c);self.mapping_events.append(dict(event='protect',address=a,bytes=b,permissions=c));return 0
  if n==215:
   assert p is self.root;u.mem_unmap(a,b);p.mappings.remove((a,b));self.mapping_events.append(dict(event='unmap_parent_copy',address=a,bytes=b));return 0
  if n==220:return self.clone(g,args)
  if n==260:
   assert p is self.collector
   if a==-1:eligible=[x for x in self.processes.values() if x.parent==p.pid and not x.reaped]
   else:eligible=[x for x in self.processes.values() if x.parent==p.pid and x.pid==a and not x.reaped and x.exit_signal==0]
   if not eligible:r=-10;status=None
   elif eligible[0].alive:r=0;status=None
   else:q=eligible[0];q.reaped=True;r=q.pid;status=q.status;u.mem_write(b,struct.pack('<i',status))
   self.waits.append(dict(caller=p.pid,pid=a,flags=c&0xffffffff,returned=r,status=status));return r
  if n==101:
   assert tuple(struct.unpack('<qq',u.mem_read(a,16)))==(0,10000000);self.clock+=10000000
   if p is self.root:self.root_sleeps+=1;self.run_child()
   elif p is self.collector:
    if self.worker and self.worker.alive:self.worker.guest.run()
    else:g.paused=True;u.emu_stop()
   return 0
  if n==93:
   if p is self.root:self.root_result=a&255;self.after_root_FDs=dict(p.fds);u.emu_stop();return 0
   status=9 if p is self.worker and self.fault=='worker-SIGKILL' else (a&255)<<8
   p.alive=False;p.status=status;self.events.append(dict(event='own child terminal',pid=p.pid,role=p.role,status=status,remaining_FDs_before_kernel_exit=sorted(p.fds)));p.fds.clear();g.exit_status=status;u.emu_stop()
   if p is self.collector and self.fault=='early-other-thread-reap':self.reap('explicit unblocked other Sony thread before observation')
   elif p is self.collector and not self.root.mask&(1<<16) and self.fault!='no-parent-reap':self.reap('SIGCHLD to already unblocked parent after return')
   return 0
  raise AssertionError(('unexpected bridge syscall',p.role,n,args))
 def summary(self,g):
  assert all(fd in self.root.fds and self.root.fds[fd] is d for fd,d in self.borrowed.items())
  return dict(result=self.root_result,fault=self.fault,root_pid=self.root.pid,root_tid=self.root.tid,original_mask=self.original_mask,final_mask=self.root.mask,clones=self.clone_events,masks=self.mask_events,mappings=self.mapping_events,root_remaining_new_FDs=sorted(set(self.root.fds)-set(self.borrowed)),root_remaining_anonymous=self.root.mappings,borrowed_FDs_unchanged=True,messages=self.messages,received=self.received,waits=self.waits,reaper=self.reaper_events,collector_status=self.collector.status if self.collector else None,collector_reaped=self.collector.reaped if self.collector else None,worker_status=self.worker.status if self.worker else None,root_sleeps=self.root_sleeps,source_accesses=self.source_accesses,original_plan_sha=self.initial_plan_sha,errors=g.errors)
class Guest:
 def __init__(self,k,p,base=0x30000000,copy_from=None):
  self.k=k;self.p=p;p.guest=self;self.raw=k.raw;self.base=base if copy_from is None else copy_from.base;self.u=U.Uc(U.UC_ARCH_ARM64,U.UC_MODE_ARM);self.errors=[];self.paused=False;self.exit_status=None
  if copy_from:
   for a,z,perm in copy_from.u.mem_regions():self.u.mem_map(a,z-a+1,perm);self.u.mem_write(a,bytes(copy_from.u.mem_read(a,z-a+1)))
   self.u.context_restore(copy_from.u.context_save())
  else:
   delta=base-D.BASE;k.original_base=base
   for s in D.read_executable(k.raw):
    perm=(U.UC_PROT_READ if s['flags']&4 else 0)|(U.UC_PROT_WRITE if s['flags']&2 else 0)|(U.UC_PROT_EXEC if s['flags']&1 else 0);self.u.mem_map(s['va']+delta,D.PAGE,perm)
    if s['filesz']:self.u.mem_write(s['va']+delta,k.raw[s['offset']:s['offset']+s['filesz']])
   self.u.mem_map(0x70000000,0x40000,U.UC_PROT_READ|U.UC_PROT_WRITE);self.u.mem_map(PLAN_AT,4096,U.UC_PROT_READ|U.UC_PROT_WRITE);self.u.mem_write(PLAN_AT,k.job);self.u.reg_write(A.UC_ARM64_REG_SP,0x7003f000);self.u.reg_write(A.UC_ARM64_REG_PC,D.HEADER.unpack_from(k.raw)[4]+delta);self.u.reg_write(A.UC_ARM64_REG_CPACR_EL1,3<<20)
  self.u.hook_add(U.UC_HOOK_INTR,self.interrupt)
 def interrupt(self,u,no,_):
  try:
   assert no==2;n=u.reg_read(A.UC_ARM64_REG_X8);a=[u.reg_read(r) for r in REG];a=[v-(1<<64) if v>>63 else v for v in a];v=self.k.syscall(self,n,a);u.reg_write(A.UC_ARM64_REG_X0,v&0xffffffffffffffff)
  except BaseException:self.errors.append(traceback.format_exc());u.emu_stop()
 def drop_original(self):
  for s in D.read_executable(self.raw):self.u.mem_unmap(self.base+s['offset'],D.PAGE)
  self.u.mem_unmap(PLAN_AT,4096)
 def run(self):
  self.paused=False;self.u.emu_start(self.u.reg_read(A.UC_ARM64_REG_PC),0,count=120_000_000);assert not self.errors,self.errors;assert self.exit_status is not None or self.paused or (self.p is self.k.root and self.k.root_result is not None),'instruction limit exhausted'
def case(raw,**kwargs):
 base=kwargs.pop('base',0x30000000);k=Kernel(raw,**kwargs);g=Guest(k,k.root,base=base);g.run();return k.summary(g)
