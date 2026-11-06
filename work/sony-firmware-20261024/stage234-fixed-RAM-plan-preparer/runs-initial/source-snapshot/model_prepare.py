"""Explicit in-memory fake filesystem/kernel; own ARM64 only.
No actual file publication, Linux process, USB, Sony or kernel execution.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,struct,sys,zlib
H=Path(__file__).resolve().parent;B=H.parent
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
M=module('sealed231_for_prepare',B/'stage231-constructor-noexec-child-and-reload-observer/model_entry.py')
D=module('prepare234_builder',H/'prepare_build.py')
U=M.U;A=M.A;Node=M.Node
PLAN='/tmp_wbshd/fx3-entry-plan-v1.bin';CLAIM='/tmp_wbshd/fx3-plan-preparation-v1';PENDING=CLAIM+'/plan.pending';REPORT=CLAIM+'/prepare.staged'
class Kernel(M.Kernel):
 def __init__(self,raw,im,fault=None):
  super().__init__(raw,im);del self.nodes[PLAN];self.prepare_fault=fault;self.allow_worker=False;self.publications=[];self.forbidden=[];self.clock_calls=0;self.created_modes=[]
  if fault=='wrong-parent':self.nodes['/proc/self/exe'].data[-1]^=1
  if fault=='image-file':self.nodes['/tmp/jiritsu/libJit.so'].data[-1]^=1
  if fault=='unsafe-root':self.nodes['/tmp_wbshd'].mode=0o40777
  if fault=='existing-plan':self.nodes[PLAN]=Node(PLAN,0o100600,b'original plan must remain')
 def syscall(self,g,n,args):
  if self.allow_worker:return super().syscall(g,n,args)
  p=g.process;u=g.u;a,b,c,d,e,f=args;fault=self.prepare_fault
  def desc(fd):return p.fds[fd]['desc']
  def cstring(at):
   data=bytearray()
   for i in range(512):
    ch=u.mem_read(at+i,1)[0]
    if not ch:return data.decode('ascii')
    data.append(ch)
   raise AssertionError('unterminated prepare path')
  if n not in [172,178,174,175,56,34,44,80,63,64,82,57,113,62,276]:self.forbidden.append(n);raise AssertionError(('forbidden in preparation',n))
  if n==63 and p.fds[a]['flags']&3==1:return -9
  if n==64 and p.fds[a]['flags']&3 not in [1,2]:return -9
  if n==62:
   assert b==c==0 and desc(a)['node'].path in [PENDING,REPORT];desc(a)['pos']=0;return 0
  if n==276:
   assert cstring(b)=='plan.pending' and cstring(d)=='fx3-entry-plan-v1.bin' and e==1 and f==0
   old=desc(a)['node'].path+'/'+cstring(b);new=desc(c)['node'].path+'/'+cstring(d);assert (old,new)==(PENDING,PLAN)
   if fault=='rename-unsupported':self.publications.append(dict(result=-38,published=False));return -38
   if fault=='publish-race':self.nodes[new]=Node(new,0o100600,b'racing plan must remain')
   if new in self.nodes:self.publications.append(dict(result=-17,published=False));return -17
   node=self.nodes.pop(old);node.path=new;node.gen+=1;self.nodes[new]=node;self.publications.append(dict(result=0,published=True,dev=node.dev,ino=node.ino))
   if fault=='post-publish-corrupt':node.data[0]^=1
   if fault=='post-publish-inode':self.nodes[new]=Node(new,node.mode,bytes(node.data))
   return 0
  if n==56:
   path=cstring(b);path=desc(a)['node'].path+'/'+path if a!=-100 else path
   if c&64:assert path in [PENDING,REPORT] and c&3==2 and c&0x80 and c&0x20000
   result=super().syscall(g,n,args)
   if result>=0 and c&64:
    if fault=='restrictive-mode' and path==PENDING:self.nodes[path].mode=0o100400
    self.created_modes.append(dict(path=path,requested=d,actual=self.nodes[path].mode&0o7777,access=c&3))
   return result
  if n==34:
   assert cstring(b)=='fx3-plan-preparation-v1' and c==0o700
   result=super().syscall(g,n,args)
   if result==0 and fault=='claim-mode':self.nodes[CLAIM].mode=0o40755
   return result
  if n==44 and fault=='non-RAM':
   result=super().syscall(g,n,args);u.mem_write(b,struct.pack('<Q',0x4d44));return result
  if n==113:
   self.clock_calls+=1
   if fault=='clock-invalid':u.mem_write(b,struct.pack('<qq',0,1_000_000_000));return 0
   if fault=='expired-before-publish' and self.clock_calls>=2:self.clock+=61_000_000_000
   if fault=='clock-backwards' and self.clock_calls>=2:self.clock=0;u.mem_write(b,bytes(16));return 0
  if n==64:
   path=desc(a)['node'].path;assert path in [PENDING,REPORT]
   if fault=='short-plan-write' and path==PENDING:return super().syscall(g,n,[a,b,120,d,e,f])
   if fault=='report-write' and path==REPORT:return -5
  if n==82 and fault=='plan-fsync' and desc(a)['node'].path==PENDING:return -5
  if n==63 and fault=='plan-readback' and desc(a)['node'].path==PENDING:
   result=super().syscall(g,n,args)
   if result>0:u.mem_write(b,b'\xff')
   return result
  if n==57:
   path=desc(a)['node'].path
   if fault=='pending-close' and path==PENDING:return -5
   if fault=='post-publish-root-close' and path=='/tmp_wbshd' and self.publications and self.publications[-1]['published']:return -5
  return super().syscall(g,n,args)
 def prepare_summary(self):
  self.summary();return dict(publications=self.publications,forbidden_syscalls=self.forbidden,created_modes=self.created_modes,remaining_new_FDs=[fd for fd in self.parent.fds if fd not in self.borrowed],files={n:dict(mode=node.mode&0o7777,bytes=len(node.data),sha256=sha256(node.data).hexdigest(),hex=bytes(node.data).hex(),dev=node.dev,ino=node.ino) for n,node in self.nodes.items() if n.startswith(CLAIM+'/') or n==PLAN},clock_calls=self.clock_calls)
class Guest(M.Guest):
 def __init__(self,raw,process,base=0x30000000):
  self.raw=raw;self.process=process;self.kernel=process.kernel;self.base=base;self.report=D.inspect_layout(raw);self.errors=[];self.trace=[];self.exitcode=None;self.blocked=False;self.unloaded=False;self.u=U.Uc(U.UC_ARCH_ARM64,U.UC_MODE_ARM);self.stop=0x71000000
  for seg in self.report['segments']:
   flags=seg['flags'];perms=(U.UC_PROT_READ if flags&4 else 0)|(U.UC_PROT_WRITE if flags&2 else 0)|(U.UC_PROT_EXEC if flags&1 else 0);self.u.mem_map(base+seg['va'],D.align(seg['memsz'],D.PAGE),perms)
   if seg['filesz']:self.u.mem_write(base+seg['va'],raw[seg['offset']:seg['offset']+seg['filesz']])
  for rel in self.report['runtime_relocations']:self.u.mem_write(base+rel['offset'],struct.pack('<Q',base+rel['addend']))
  self.u.mem_protect(base+3*D.PAGE,D.PAGE,U.UC_PROT_READ);self.u.mem_map(0x70000000,0x20000,U.UC_PROT_READ|U.UC_PROT_WRITE);self.u.mem_map(self.stop,4096,U.UC_PROT_READ|U.UC_PROT_EXEC);self.u.reg_write(A.UC_ARM64_REG_CPACR_EL1,3<<20);self.u.hook_add(U.UC_HOOK_INTR,self.interrupt)
 def status(self):return (self.call(self.report['exports']['fx3_prepare_state']['va']),self.call(self.report['exports']['fx3_prepare_reason']['va']))
