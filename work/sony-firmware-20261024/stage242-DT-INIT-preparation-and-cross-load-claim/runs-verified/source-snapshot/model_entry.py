"""Own code only; model loader entry, process/IPC and an in-memory shared VFS.
No native dlopen, Linux or original firmware instruction is executed.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,struct,sys,traceback
import entry_build as D
H=Path(__file__).resolve().parent;B=H.parent
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=sys.modules.get('bridge_build');sys.modules['bridge_build']=D
try:M=module('own240_for_242',B/'stage240-runtime-plan-and-anonymous-clone-bridge/model_bridge.py')
finally:
 if old is None:sys.modules.pop('bridge_build',None)
 else:sys.modules['bridge_build']=old
M.D=D;U=M.U;A=M.A
ROOT='/tmp_wbshd';CLAIM=ROOT+'/fx3-plan-preparation-v1';PLAN=ROOT+'/fx3-entry-plan-v1.bin'
PENDING=CLAIM+'/plan.pending';STAGED=CLAIM+'/prepare.staged';IMAGE='/tmp/jiritsu/libJit.so'
class Node:
 next_ino=100000
 def __init__(self,path,mode,data=b'',ram=False):
  self.path=path;self.mode=mode;self.data=bytearray(data);self.ram=ram;self.uid=0;self.nlink=1;self.ino=Node.next_ino;Node.next_ino+=1;self.gen=1
class Filesystem:
 def __init__(self,raw,im):self.nodes={ROOT:Node(ROOT,0o41777,ram=True),IMAGE:Node(IMAGE,0o100600,raw),'/proc/self/exe':Node('/proc/self/exe',0o100755,im)};self.claims=[]
class Kernel(M.Kernel):
 def __init__(self,raw,im,fs=None,prepare_fault=None,**kwargs):
  super().__init__(raw,**kwargs);self.fs=fs or Filesystem(raw,im);self.prepare_fault=prepare_fault;self.file_events=[];self.publications=[];self.clock_calls=0;self.original_published_plan=None;self.after_claim=None;self.other_results=[]
  if prepare_fault=='wrong-parent':self.fs.nodes['/proc/self/exe'].data[-1]^=1
  if prepare_fault=='image-file':self.fs.nodes[IMAGE].data[3*D.PAGE-1]^=1
  if prepare_fault=='mutable-file-padding':self.fs.nodes[IMAGE].data[-4097]^=1
  if prepare_fault=='unsafe-root':self.fs.nodes[ROOT].mode=0o40777
  if prepare_fault=='non-RAM':self.fs.nodes[ROOT].ram=False
  if prepare_fault=='existing-plan':self.fs.nodes[PLAN]=Node(PLAN,0o100600,b'preexisting plan',True)
 def syscall(self,g,n,args):
  p=g.p;u=g.u;a,b,c,d,e,f=args;fault=self.prepare_fault
  def text(at):
   out=bytearray()
   for i in range(512):
    v=u.mem_read(at+i,1)[0]
    if not v:return out.decode('ascii')
    out.append(v)
   raise AssertionError('unterminated own pathname')
  def desc(fd):return p.fds[fd]
  def regular(fd):return fd in p.fds and p.fds[fd].get('kind')=='vfs'
  def pathat(fd,at):
   s=text(at)
   return s if fd==-100 else desc(fd)['node'].path+'/'+s
  if n==56:
   path=pathat(a,b) if a==-100 or regular(a) else None
   if path is not None and (path in self.fs.nodes or path in [ROOT,CLAIM,PLAN,PENDING,STAGED,IMAGE,'/proc/self/exe']):
    node=self.fs.nodes.get(path)
    if c&64:
     assert path in [PENDING,STAGED] and c&0x80 and c&0x20000 and c&3==2 and d==0o600
     if node is not None:return -17
     node=Node(path,0o100600,ram=True);self.fs.nodes[path]=node
     if fault=='restrictive-mode' and path==PENDING:node.mode=0o100400
    if node is None:return -2
    if c&0x10000 and node.mode&0o170000!=0o40000:return -20
    fd=p.fd(dict(kind='vfs',node=node,pos=0,flags=c,cloexec=int(bool(c&0x80000))))
    self.file_events.append(dict(op='open',role=p.role,path=path,fd=fd,flags=c));return fd
  if n==34:
   path=pathat(a,b);assert path==CLAIM and c==0o700
   if path in self.fs.nodes:self.fs.claims.append(dict(pid=p.pid,result=-17));return -17
   self.fs.nodes[path]=Node(path,0o40700,ram=True);self.fs.claims.append(dict(pid=p.pid,result=0))
   if fault=='claim-mode':self.fs.nodes[path].mode=0o40755
   if self.after_claim:
    callback=self.after_claim;self.after_claim=None;callback()
   return 0
  if n in [80,44,63,64,62,82,57] and regular(a):
   row=desc(a);node=row['node'];path=node.path
   if n==80:
    v=bytearray(128);struct.pack_into('<QQIIII',v,0,9,node.ino,node.mode,node.nlink,node.uid,0);struct.pack_into('<q',v,48,len(node.data));struct.pack_into('<qqq',v,88,node.gen,0,node.gen);u.mem_write(b,bytes(v));return 0
   if n==44:
    v=[0]*15;v[0]=0x01021994 if node.ram else 0x4d44;v[1]=v[9]=4096;v[4]=100000;u.mem_write(b,struct.pack('<15Q',*v));return 0
   if n==63:
    if row['flags']&3==1:return -9
    data=bytes(node.data[row['pos']:row['pos']+c]);row['pos']+=len(data)
    if fault=='plan-readback' and path==PENDING and data:data=b'\xff'+data[1:]
    if data:u.mem_write(b,data)
    return len(data)
   if n==64:
    assert path in [PENDING,STAGED]
    if row['flags']&3 not in [1,2]:return -9
    if fault=='report-write' and path==STAGED:return -5
    size=120 if fault=='short-plan-write' and path==PENDING else c
    data=bytes(u.mem_read(b,size));end=row['pos']+size
    if end>len(node.data):node.data.extend(bytes(end-len(node.data)))
    node.data[row['pos']:end]=data;row['pos']=end;node.gen+=1
    self.file_events.append(dict(op='write',path=path,bytes=size));return size
   if n==62:assert b==c==0;row['pos']=0;return 0
   if n==82:return -5 if fault=='plan-fsync' and path==PENDING else 0
   if n==57:
    del p.fds[a];self.file_events.append(dict(op='close',role=p.role,path=path,fd=a))
    if fault=='pending-close' and path==PENDING:return -5
    if self.publications and path==ROOT:
     if fault=='post-publish-root-close':return -5
     if fault=='expire-during-final-close':self.clock+=61_000_000_000
     if fault=='mutate-published-after-prepare':self.fs.nodes[PLAN].data[32]^=1
    return 0
  if n==276:
   old=pathat(a,b);new=pathat(c,d);assert (old,new,e,f)==(PENDING,PLAN,1,0)
   if fault=='rename-unsupported':return -38
   if fault=='publish-race':self.fs.nodes[new]=Node(new,0o100600,b'racing plan',True)
   if new in self.fs.nodes:return -17
   node=self.fs.nodes.pop(old);node.path=new;node.gen+=1;self.fs.nodes[new]=node;self.original_published_plan=bytes(node.data);self.initial_plan_sha=sha256(node.data).hexdigest();self.job=bytes(node.data);self.publications.append(dict(path=new,bytes=len(node.data),sha256=self.initial_plan_sha))
   if fault=='post-publish-corrupt':node.data[0]^=1
   if fault=='post-publish-inode':self.fs.nodes[new]=Node(new,node.mode,node.data,True)
   if fault=='expire-after-publish':self.clock+=61_000_000_000
   return 0
  if n==113:
   self.clock_calls+=1
   if fault=='clock-invalid':u.mem_write(b,struct.pack('<qq',0,1_000_000_000));return 0
   if fault=='expired-before-publish' and self.clock_calls>=2:self.clock+=61_000_000_000
  return super().syscall(g,n,args)
 def summary(self,g):
  v=super().summary(g);v.update(prepare_fault=self.prepare_fault,file_events=self.file_events,publications=self.publications,claims=list(self.fs.claims),other_results=self.other_results,clock_calls=self.clock_calls,files={name:dict(mode=node.mode,bytes=len(node.data),sha256=sha256(node.data).hexdigest(),hex=bytes(node.data).hex(),ino=node.ino) for name,node in self.fs.nodes.items() if name.startswith(CLAIM+'/') or name==PLAN},full_file_sha256=sha256(self.raw).hexdigest(),observed_image_file_sha256=sha256(self.fs.nodes[IMAGE].data).hexdigest(),immutable_image_id=sha256(self.raw[:3*D.PAGE]+bytes(D.PAGE)).hexdigest(),original_published_plan_sha256=sha256(self.original_published_plan).hexdigest() if self.original_published_plan else None,original_Sony_im_file_hashed_not_executed=True,borrowed_FDs_unchanged=True);return v
class Guest(M.Guest):
 def __init__(self,k,p,base=0x30000000,copy_from=None):
  super().__init__(k,p,base,copy_from)
  if copy_from is None:self.u.mem_unmap(M.PLAN_AT,4096)
 def drop_original(self):
  for s in D.read_executable(self.raw):self.u.mem_unmap(self.base+s['offset'],D.PAGE)
 def run(self):
  self.paused=False;self.u.emu_start(self.u.reg_read(A.UC_ARM64_REG_PC),0,count=350_000_000)
  assert not self.errors,self.errors
  assert self.exit_status is not None or self.paused or (self.p is self.k.root and self.k.root_result is not None),'instruction limit exhausted'
M.Guest=Guest
def case(raw,im,**kwargs):
 base=kwargs.pop('base',0x30000000);k=Kernel(raw,im,**kwargs);g=Guest(k,k.root,base=base);g.run();return k,g,k.summary(g)
