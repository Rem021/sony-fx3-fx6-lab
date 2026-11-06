"""Execute ONLY our ARM64 collector/NOOP in an explicit fake Linux kernel.
Parent eligibility is derived from a process tree, not injected wait returns.
The illegal-parent-injection case deliberately violates the closed-tree input
and is retained as an admission boundary, never hidden by positive tests.
"""
from pathlib import Path
from collections import deque
from hashlib import sha256
import json,struct,traceback
import unicorn as U
import unicorn.arm64_const as A
import isolated_build as D
H=Path(__file__).resolve().parent
REG=[getattr(A,'UC_ARM64_REG_X'+str(n)) for n in range(6)]
BLOCKED=((1<<64)-1)&~((1<<8)|(1<<18))
def cmsg(kind,p):
 x=struct.pack('<QII',16+len(p),1,kind)+p;return x+bytes((-len(x))%8)
class Process:
 def __init__(self,pid,parent,role):
  self.pid=self.tid=pid;self.parent=parent;self.role=role;self.fds={};self.nextfd=10;self.mask=BLOCKED;self.actions={17:b'\x01'+bytes(31)};self.subreaper=False;self.threads=1;self.tracer=0;self.alive=True;self.reaped=False;self.status=None;self.guest=None
 def fd(self,d):
  while self.nextfd in self.fds:self.nextfd+=1
  n=self.nextfd;self.nextfd+=1;self.fds[n]=d;return n
class Kernel:
 def __init__(self,raw,fault=None):
  self.raw=raw;self.fault=fault;self.clock=1_000_000_000;self.sleeps=0;self.events=[];self.syscalls=[];self.waits=[];self.closes=[];self.rights=[];self.source_accesses=[];self.worker=None;self.swapped=False;self.between=False;self.host=Process(321,1,'Sony host represented as data only');self.collector=Process(5001,321,'own collector');self.processes={321:self.host,5001:self.collector}
  for fd in [0,1,2,7,9]:self.host.fds[fd]=dict(kind='borrowed',name=str(fd))
  self.collector.fds=dict(self.host.fds);self.host_before=dict(self.host.fds)
  if fault=='multi-thread':self.collector.threads=2
  if fault=='tid-mismatch':self.collector.tid=5002
  if fault=='subreaper':self.collector.subreaper=True
  if fault=='traced':self.collector.tracer=88
  if fault=='unblocked':self.collector.mask=0x400
  if fault=='existing-child':self.processes[6666]=Process(6666,5001,'preexisting')
 def terminate(self,p,status,kind):
  p.alive=False;p.status=status;self.events.append(dict(event='kernel task terminal',role=p.role,pid=p.pid,status=status,kind=kind,closed_FDs=sorted(p.fds)));p.fds.clear();p.guest.exit_status=status;p.guest.u.emu_stop()
 def run_worker(self):
  if self.worker and self.worker.alive:
   if self.fault=='stall':return
   if self.fault=='late-zero' and self.sleeps<105:return
   self.worker.guest.run()
 def syscall(self,g,n,args):
  p=g.p;u=g.u;a,b,c,d,e,f=args;self.syscalls.append((p.role,n))
  def string(at):
   out=bytearray()
   for _ in range(1024):
    x=u.mem_read(at+len(out),1)[0]
    if not x:return out.decode('ascii')
    out.append(x)
   raise AssertionError('unterminated own string')
  if n==172:return p.pid
  if n==178:return p.tid
  if n==173:return p.parent
  if n in (174,175):return 0
  if n==113:
   self.clock+=1000;u.mem_write(b,struct.pack('<qq',self.clock//10**9,self.clock%10**9));return 0
  if n==135:
   assert a==2 and d==8 and not b
   u.mem_write(c,struct.pack('<Q',p.mask));return 0
  if n==134:
   assert p is self.collector and a not in (9,19) and d==8
   if b:p.actions[a]=bytes(u.mem_read(b,32))
   if c:u.mem_write(c,p.actions.get(a,bytes(32)))
   return 0
  if n==167:
   assert p is self.collector and a==37
   if self.fault=='prctl-unavailable':return -22
   u.mem_write(b,struct.pack('<i',int(p.subreaper)));return 0
  if n==56:
   path=string(b);assert a==-100
   if path=='/proc/self/status':
    if self.fault=='status-open':return -2
    data=f'Name:\tisolated\nTgid:\t{p.pid}\nPid:\t{p.pid}\nPPid:\t{p.parent}\nTracerPid:\t{p.tracer}\nThreads:\t{p.threads}\n'.encode()
    return p.fd(dict(kind='status',data=data,pos=0))
   if path=='/proc/self/fd':return p.fd(dict(kind='scan',entries=None,pos=0))
   self.source_accesses.append(path);raise AssertionError('unapproved source opened: '+path)
  if n==63:
   row=p.fds[a];assert row['kind']=='status';data=row['data'][row['pos']:row['pos']+c];row['pos']+=len(data);u.mem_write(b,data);return len(data)
  if n==61:
   row=p.fds[a];assert row['kind']=='scan'
   if row['entries'] is None:row['entries']=['.','..']+[str(x) for x in sorted(p.fds)]
   out=bytearray()
   while row['pos']<len(row['entries']):
    name=row['entries'][row['pos']].encode()+b'\0';size=(19+len(name)+7)&~7
    if len(out)+size>c:break
    out+=struct.pack('<QqHB',1,row['pos']+1,size,0)+name+bytes(size-19-len(name));row['pos']+=1
   u.mem_write(b,bytes(out));return len(out)
  if n==57:
   if a not in p.fds:return -9
   row=p.fds.pop(a);self.closes.append(dict(role=p.role,fd=a,kind=row['kind']))
   if row['kind']=='socket' and p is self.worker and row['side']=='right' and self.fault in ('worker-close-error','external-reap-cousin','external-reap-host-child','illegal-parent-injection'):return -5
   if row['kind']=='socket' and p is self.collector and row['side']=='left' and self.fault=='collector-close-error':return -5
   return 0
  if n==199:
   assert p is self.collector and (a,b,c)==(1,0x80002,0)
   left=dict(kind='socket',side='left',queue=deque());right=dict(kind='socket',side='right',queue=deque());left['peer']=right;right['peer']=left
   x=p.fd(left);y=p.fd(right);u.mem_write(d,struct.pack('<ii',x,y));return 0
  if n==208:
   assert (b,c,e)==(1,16,4);assert struct.unpack('<I',u.mem_read(d,4))[0]==1
   p.fds[a]['passcred']=True;return 0
  if n in (211,212):
   row=p.fds[a];assert row['kind']=='socket';_,_,iov,ilen,control,clen,_=struct.unpack('<QI4xQQQQI4x',u.mem_read(b,56));ptr,size=struct.unpack('<QQ',u.mem_read(iov,16));assert ilen==1 and size==256
   if n==211:
    if p is self.collector and self.fault=='GO-send-error':return -5
    data=bytes(u.mem_read(ptr,size));row['peer']['queue'].append((data,p.pid));self.events.append(dict(event='private message',sender=p.pid,type=struct.unpack_from('<I',data,20)[0]));return size
   assert c&64 and row.get('passcred')
   if not row['queue']:return -11
   data,sender=row['queue'].popleft()
   if p is self.collector and self.fault=='wrong-DONE':sender=6666
   ctl=cmsg(2,struct.pack('<III',sender,0,0))
   if p is self.collector and self.fault=='SCM-rights':
    fd=p.fd(dict(kind='injected-right'));self.rights.append(fd);ctl+=cmsg(1,struct.pack('<I',fd))
   assert len(ctl)<=clen;u.mem_write(ptr,data);u.mem_write(control,ctl);u.mem_write(b+40,struct.pack('<Q',len(ctl)));u.mem_write(b+48,struct.pack('<I',0));return size
  if n==220:
   assert p is self.collector and args==[0]*6 and self.worker is None
   ch=Process(7002,p.pid,'own worker');ch.mask=p.mask;ch.actions=dict(p.actions);ch.fds=dict(p.fds);ch.nextfd=p.nextfd;cg=Guest(self,ch,copy_from=g);cg.u.reg_write(A.UC_ARM64_REG_X0,0);ch.guest=cg;self.worker=ch;self.processes[ch.pid]=ch
   self.events.append(dict(event='clone0',parent=p.pid,child=ch.pid,private_VM_FDs_sighand=True,new_child_list_empty=True,new_subreaper=False));return ch.pid
  if n==260:
   assert p is self.collector and c&0xffffffff in (0x40000001,0xa0000001)
   if a==-1:
    eligible=[x for x in self.processes.values() if x.parent==p.pid and not x.reaped]
   else:
    if self.fault=='between-recv-wait' and not self.between:self.between=True;self.run_worker()
    if self.fault=='collector-killed':self.terminate(p,9,'SIGKILL');return 0
    if self.worker and not self.worker.alive and not self.swapped and self.fault in ('external-reap-cousin','external-reap-host-child','illegal-parent-injection'):
     self.worker.reaped=True;foreign_parent=1 if self.fault=='external-reap-cousin' else (321 if self.fault=='external-reap-host-child' else p.pid)
     q=Process(self.worker.pid,foreign_parent,'foreign replacement');q.alive=False;q.status=0;self.processes[q.pid]=q;self.swapped=True
     self.events.append(dict(event='explicit external tracer reaps worker and creates replacement',own_status=self.worker.status,replacement_parent=foreign_parent,closed_tree_contract_violated=self.fault=='illegal-parent-injection'))
    eligible=[x for x in self.processes.values() if x.pid==a and x.parent==p.pid and not x.reaped]
   if not eligible:r=-10;status=None
   elif eligible[0].alive:r=0;status=None
   else:
    q=eligible[0];q.reaped=True;r=q.pid;status=q.status;u.mem_write(b,struct.pack('<i',status))
   self.waits.append(dict(request=a,options=c&0xffffffff,eligible_roles=[q.role for q in eligible],returned=r,status=status));return r
  if n==101:
   assert tuple(struct.unpack('<qq',u.mem_read(a,16)))==(0,10000000)
   self.clock+=10000000
   if p is self.collector:
    self.sleeps+=1;self.run_worker()
    if self.sleeps>=120:g.paused=True;u.emu_stop()
   return 0
  if n==93:
   if p is self.worker and a==0 and self.fault=='SIGKILL-after-DONE':self.terminate(p,9,'SIGKILL after DONE')
   else:self.terminate(p,(a&255)<<8,'SYS_exit')
   return 0
  raise AssertionError(('unexpected own syscall',p.role,n,args))
 def summary(self):
  assert self.host.fds==self.host_before
  return dict(fault=self.fault,collector_exit_status=self.collector.status,collector_alive=self.collector.alive,
    collector_state=self.collector.guest.state(),own_worker_status=self.worker.status if self.worker else None,
    own_worker_alive=self.worker.alive if self.worker else None,worker_reaped=self.worker.reaped if self.worker else None,
    collector_remaining_FDs=sorted(self.collector.fds),host_borrowed_FDs_unchanged=True,private_messages=[e for e in self.events if e['event']=='private message'],
    events=self.events,waits=self.waits,source_accesses=self.source_accesses,collector_sleeps=self.sleeps,
    only_collector_created_child=not any(role=='own worker' and n==220 for role,n in self.syscalls),
    injected_rights_all_closed=all(fd not in self.collector.fds for fd in self.rights),syscall_count=len(self.syscalls))
class Guest:
 def __init__(self,k,p,copy_from=None):
  self.k=k;self.p=p;p.guest=self;self.u=U.Uc(U.UC_ARCH_ARM64,U.UC_MODE_ARM);self.errors=[];self.exit_status=None;self.paused=False
  if copy_from:
   for a,z,perm in copy_from.u.mem_regions():self.u.mem_map(a,z-a+1,perm);self.u.mem_write(a,bytes(copy_from.u.mem_read(a,z-a+1)))
   self.u.context_restore(copy_from.u.context_save())
  else:
   for s in D.read_executable(k.raw):
    perm=(U.UC_PROT_READ if s['flags']&4 else 0)|(U.UC_PROT_WRITE if s['flags']&2 else 0)|(U.UC_PROT_EXEC if s['flags']&1 else 0);self.u.mem_map(s['va'],D.align(s['memsz'],D.PAGE),perm)
    if s['filesz']:self.u.mem_write(s['va'],k.raw[s['offset']:s['offset']+s['filesz']])
   self.u.mem_map(0x70000000,0x20000,U.UC_PROT_READ|U.UC_PROT_WRITE);self.u.reg_write(A.UC_ARM64_REG_SP,0x7001f000);self.u.reg_write(A.UC_ARM64_REG_PC,D.HEADER.unpack_from(k.raw)[4]);self.u.reg_write(A.UC_ARM64_REG_CPACR_EL1,3<<20)
  self.u.hook_add(U.UC_HOOK_INTR,self.interrupt)
 def interrupt(self,u,no,_):
  try:
   assert no==2;n=u.reg_read(A.UC_ARM64_REG_X8);args=[u.reg_read(r) for r in REG];args=[v-(1<<64) if v>>63 else v for v in args];v=self.k.syscall(self,n,args);u.reg_write(A.UC_ARM64_REG_X0,v&0xffffffffffffffff)
  except BaseException:self.errors.append(traceback.format_exc());u.emu_stop()
 def run(self):
  if not self.p.alive:return
  self.u.emu_start(self.u.reg_read(A.UC_ARM64_REG_PC),0,count=8_000_000)
  assert not self.errors,self.errors
  assert self.exit_status is not None or self.paused,'own instruction budget exhausted'
 def state(self):
  s=D.read_executable(self.k.raw)[-1];return struct.unpack('<I',self.u.mem_read(s['va'],4))[0]
def case(raw,fault=None):
 k=Kernel(raw,fault);g=Guest(k,k.collector);g.run();return k.summary()
