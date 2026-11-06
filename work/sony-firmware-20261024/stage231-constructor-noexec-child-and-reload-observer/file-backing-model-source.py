"""Explicit in-memory fake Linux; only own ARM64 executes in Unicorn.
No OS processes, threads, USB objects, source devices or Sony code are run.
The scheduler deliberately lets the parent unload BEFORE running its child.
"""
from pathlib import Path
from hashlib import sha256
from collections import deque
import importlib.util,json,struct,sys,zlib,traceback
import unicorn as U
from unicorn import arm64_const as A
H=Path(__file__).resolve().parent;R=H.parents[2]
spec=importlib.util.spec_from_file_location('entry231_builder',H/'entry_build.py');D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
REG=[getattr(A,'UC_ARM64_REG_X'+str(i)) for i in range(6)]
class Blocked(Exception):pass
class Node:
 serial=2000
 def __init__(self,path,mode,data=b''):
  self.path=path;self.mode=mode;self.data=bytearray(data);Node.serial+=1;self.ino=Node.serial;self.dev=9;self.uid=0;self.nlink=1;self.gen=1
 def stat(self):
  out=bytearray(128);struct.pack_into('<QQIIIIQQq',out,0,self.dev,self.ino,self.mode,self.nlink,self.uid,0,0,0,len(self.data));struct.pack_into('<qQqQ',out,88,self.gen,0,self.gen,0);return bytes(out)
def task(raw,operation=1,nonce=b'\xbb'*16):
 out=bytearray(256);out[:16]=b'FX3ENTRYPLANv1'.ljust(16,b'\0');struct.pack_into('<IIII',out,16,1,operation,1,0);out[32:48]=nonce;out[48:80]=b'\xcc'*32;out[80:112]=b'\xdd'*32;out[112:144]=sha256(raw).digest();struct.pack_into('<QQI',out,144,1_000_000_000,901_000_000_000,1);struct.pack_into('<I',out,252,zlib.crc32(out[:252]));return bytes(out)
def cmsg(kind,body):
 data=struct.pack('<QII',16+len(body),1,kind)+body;return data+bytes((-len(data))%8)
class Process:
 def __init__(self,k,pid=321,tid=777):
  self.kernel=k;self.pid=pid;self.tid=tid;self.ppid=1;self.fds={};self.nextfd=10;self.mask=0x400;self.actions={17:struct.pack('<QQQQ',0x402f4c,0,0,0)};self.alive=True;self.exit_signal=17;self.exit_status=None;self.reaped=False;self.guest=None;self.generation=1;self.creator_node=None
  if pid==321:
   for fd in [0,1,2,7,9]:self.fds[fd]=dict(desc=dict(node=Node('borrowed:'+str(fd),0o100600),pos=0,kind='file'),flags=(fd&1)*0x80000)
 def thread_node(self):
  key=(self.pid,self.tid,self.generation)
  if key not in self.kernel.thread_nodes:self.kernel.thread_nodes[key]=Node("/proc/self/task/"+str(self.tid),0o40555)
  return self.kernel.thread_nodes[key]
 def fd(self,desc,flags=0):
  while self.nextfd in self.fds:self.nextfd+=1
  fd=self.nextfd;self.nextfd+=1;self.fds[fd]=dict(desc=desc,flags=flags);return fd
class Kernel:
 def __init__(self,raw,im,fault=None):
  self.raw=raw;self.im=im;self.fault=fault;self.clock=1_000_000_000;self.thread_nodes={};self.pid_reused=False;self.parent=Process(self);self.child=None;self.clone_events=[];self.waits=[];self.reaper=[];self.signal_ops=[];self.send_events=[];self.close_events=[];self.exec_attempts=[];self.source_accesses=[];self.syscalls=[];self.rights=[];self.child_FD_sets=[];self.exit_cleanup=[];self.anonymous_mappings=[];self.protection_changes=[]
  self.nodes={p:Node(p,m,d) for p,m,d in [('/tmp_wbshd',0o41777,b''),('/tmp/jiritsu/libJit.so',0o100755,raw),('/proc/self/exe',0o100755,im),('/tmp_wbshd/fx3-entry-plan-v1.bin',0o100600,task(raw))]}
  self.borrowed={fd:(row['desc'],row['flags']) for fd,row in self.parent.fds.items()}
  if fault=='bad-plan':self.nodes['/tmp_wbshd/fx3-entry-plan-v1.bin'].data[-1]^=1
  if fault=='image-file':self.nodes['/tmp/jiritsu/libJit.so'].data[-1]^=1
 def plan(self,operation=2,nonce=b'\xbb'*16):
  p=self.nodes['/tmp_wbshd/fx3-entry-plan-v1.bin'];p.data[:]=task(self.raw,operation,nonce);p.gen+=1
 def fail(self):return -5
 def im_reap(self,all_children=False):
  p=self.child;eligible=bool(p and not p.alive and not p.reaped and p.ppid==321 and (all_children or p.exit_signal==17))
  self.reaper.append(dict(all_children=all_children,eligible=eligible,exit_signal=p.exit_signal if p else None))
  if eligible:p.reaped=True
 def clone(self,guest,args):
  assert args==[0,0,0,0,0,0];parent=guest.process;assert parent.pid==321 and self.child is None
  child=Process(self,7001,7001);child.ppid=321;child.creator_node=parent.thread_node();child.fds={fd:dict(row) for fd,row in parent.fds.items()};child.nextfd=parent.nextfd;child.mask=parent.mask;child.actions=dict(parent.actions);child.exit_signal=0
  cg=Guest(self.raw,child,base=guest.base,copy_from=guest);child.guest=cg;cg.u.reg_write(A.UC_ARM64_REG_X0,0);self.child=child
  self.clone_events.append(dict(flags=0,shared_VM=False,shared_FD_table=False,shared_sighand=False,parent_mask=parent.mask,child_mask=child.mask,child_pid=7001));return 7001
 def syscall(self,g,n,args):
  p=g.process;u=g.u;a,b,c,d,e,f=args;self.syscalls.append((p.pid,n))
  def string(at):
   out=bytearray()
   for i in range(1024):
    v=u.mem_read(at+i,1)[0]
    if not v:return out.decode('ascii')
    out.append(v)
   raise AssertionError('unterminated guest string')
  def desc(fd):return p.fds[fd]['desc']
  if n==172:return p.pid
  if n==173:return p.ppid
  if n==178:return p.tid
  if n in (174,175):return 0
  if n==113:self.clock+=1000;u.mem_write(b,struct.pack('<qq',self.clock//10**9,self.clock%10**9));return 0
  if n==56:
   path=string(b)
   if a!=-100:path=desc(a)['node'].path+'/'+path
   if path.startswith('/dev/') or path.startswith('/kmod/') or path=='/proc/partitions':self.source_accesses.append(path);raise AssertionError('source access in NOOP entry diagnostic')
   if path.startswith('/proc/self/task/'):
    assert int(path.rsplit('/',1)[1])==p.tid;return p.fd(dict(node=p.thread_node(),kind='procdir',pos=0),c)
   if path=='/proc/self/fd':return p.fd(dict(node=Node(path,0o40500),kind='fdscan',entries=None,pos=0),c)
   if path not in self.nodes:
    if not c&64:return -2
    self.nodes[path]=Node(path,0o100000|d)
   elif c&64 and c&128:return -17
   node=self.nodes[path]
   if c&0x10000 and node.mode&0o170000!=0o40000:return -20
   return p.fd(dict(node=node,kind='file',pos=0),c)
  if n==34:
   path=desc(a)['node'].path+'/'+string(b)
   if path in self.nodes:return -17
   self.nodes[path]=Node(path,0o40000|c);return 0
  if n==44:
   node=desc(a)['node'];assert node.path.startswith(('/tmp_wbshd','/proc/self/task/'));v=[0]*32;v[0]=0x9fa0 if node.path.startswith('/proc/') else 0x01021994;v[1]=v[9]=4096;v[4]=65536;u.mem_write(b,struct.pack('<32Q',*v));return 0
  if n==80:
   if a not in p.fds:return -9
   u.mem_write(b,desc(a)['node'].stat());return 0
  if n==63:
   row=desc(a);data=bytes(row['node'].data[row['pos']:row['pos']+c]);row['pos']+=len(data);u.mem_write(b,data);return len(data)
  if n==64:
   row=desc(a);node=row['node'];assert node.path.startswith('/tmp_wbshd/');data=bytes(u.mem_read(b,c));pos=row['pos'];node.data[pos:pos+c]=data;row['pos']+=c;node.gen+=1;return c
  if n==82:return 0
  if n==57:
   if a not in p.fds:return -9
   row=desc(a);self.close_events.append(dict(pid=p.pid,fd=a,kind=row['kind']))
   if self.fault=='child-control-close' and p.pid==7001 and row['kind']=='socket' and row['node'].path=='socket:right':return -5
   del p.fds[a];return 0
  if n==61:
   row=desc(a);assert row['kind']=='fdscan'
   if row['entries'] is None:row['entries']=['.','..']+[str(fd) for fd in sorted(p.fds)]
   out=bytearray()
   while row['pos']<len(row['entries']):
    name=row['entries'][row['pos']].encode()+b'\0';length=(19+len(name)+7)&~7
    if len(out)+length>c:break
    out+=struct.pack('<QqHB',1,row['pos']+1,length,0)+name+bytes(length-19-len(name));row['pos']+=1
   u.mem_write(b,bytes(out));return len(out)
  if n==135:
   assert a==2 and d==8
   old=p.mask
   if b:
    value=struct.unpack('<Q',u.mem_read(b,8))[0]
    if p.pid==321 and value==0x400 and (self.fault=='parent-mask-restore' or self.fault=='observer-mask-restore' and self.waits):return -1
    p.mask=value
   if c:u.mem_write(c,struct.pack('<Q',old))
   return 0
  if n==134:
   assert p.pid==7001 and a not in (9,19) and d==8;self.signal_ops.append(dict(pid=p.pid,signal=a,set=bool(b)))
   if b:p.actions[a]=bytes(u.mem_read(b,32))
   if c:u.mem_write(c,p.actions.get(a,bytes(32)))
   return 0
  if n==199:
   assert (a,b,c)==(1,0x80002,0);left=dict(node=Node('socket:left',0o140600),kind='socket',queue=deque(),creator=p.pid);right=dict(node=Node('socket:right',0o140600),kind='socket',queue=deque(),creator=p.pid);left['peer']=right;right['peer']=left
   x=p.fd(left,0x80000);y=p.fd(right,0x80000);u.mem_write(d,struct.pack('<ii',x,y));return 0
  if n==209:
   row=desc(a);assert row['kind']=='socket' and b==1
   if c==3:u.mem_write(d,struct.pack('<I',2));u.mem_write(e,struct.pack('<I',4));return 0
   if c==17:u.mem_write(d,struct.pack('<III',row['creator'],0,0));u.mem_write(e,struct.pack('<I',12));return 0
   raise AssertionError(('getsockopt',c))
  if n==204:u.mem_write(b,struct.pack('<H',1));u.mem_write(c,struct.pack('<I',2));return 0
  if n==208:assert (b,c)==(1,16);return 0
  if n in (211,212):
   row=desc(a);assert row['kind']=='socket';name,nlen,iov,ilen,control,clen,flags=struct.unpack('<QI4xQQQQI4x',u.mem_read(b,56));ptr,size=struct.unpack('<QQ',u.mem_read(iov,16));assert size==256 and ilen==1
   if n==211:
    data=bytes(u.mem_read(ptr,size));row['peer']['queue'].append((data,p.pid));self.send_events.append(dict(pid=p.pid,kind=struct.unpack_from('<I',data,20)[0],bytes=len(data)));return len(data)
   if p.pid==7001:self.child_FD_sets.append(sorted(p.fds))
   if not row['queue']:
    if c&64:return -11
    raise Blocked('child is blocked on the original private GRANT')
   data,sender=row['queue'].popleft()
   creds=cmsg(2,struct.pack('<III',sender if self.fault!='wrong-DONE-cred' or p.pid!=321 else 321,0,0))
   if self.fault in ('SCM-rights','short-with-rights') and p.pid==321:
    newfd=p.fd(dict(node=Node('injected-right',0o100600),kind='file',pos=0),0x80000);self.rights.append(newfd);creds+=cmsg(1,struct.pack('<I',newfd))
    if self.fault=='short-with-rights':data=data[:120]
   assert len(creds)<=clen;u.mem_write(ptr,data[:size]);u.mem_write(control,creds);u.mem_write(b+40,struct.pack('<Q',len(creds)));u.mem_write(b+48,struct.pack('<I',0));return len(data)
  if n==222:
   assert p.pid==321 and (a,c,d,e,f)==(0,3,0x22,-1,0) and b==196608;address=0x50001000;u.mem_map(address,b,U.UC_PROT_READ|U.UC_PROT_WRITE);self.anonymous_mappings.append(dict(address=address,bytes=b));return address
  if n==226:
   assert p.pid==321 and not (c&2 and c&4);u.mem_protect(a,b,c);self.protection_changes.append(dict(address=a,bytes=b,permissions=c));return 0
  if n==215:
   assert p.pid==321;u.mem_unmap(a,b);return 0
  if n==220:return self.clone(g,args)
  if n==260:
   assert p.pid==321 and c&0xffffffff in (0x80000001,0xa0000001)
   if self.fault=='PID-reuse-at-wait' and not self.pid_reused:
    old=self.child;assert old and not old.alive;old.reaped=True;ch=Process(self,7001,7001);ch.ppid=321;ch.alive=False;ch.exit_status=0;ch.exit_signal=0;ch.creator_node=Node('foreign im thread888',0o40555);ch.guest=old.guest;self.child=ch;self.pid_reused=True
   ch=self.child
   if not ch or a!=ch.pid or ch.reaped:value=-10
   elif ch.exit_signal==17:value=-10
   elif c&0x20000000 and ch.creator_node is not p.thread_node():value=-10
   elif ch.alive:value=0
   else:value=ch.pid;ch.reaped=True;u.mem_write(b,struct.pack('<i',ch.exit_status))
   self.waits.append(dict(pid=a,options=c&0xffffffff,returned=value,status=ch.exit_status if value>0 else None));return value
  if n==93:
   assert p.pid==7001;p.alive=False;p.exit_status=(a&255)<<8;self.exit_cleanup.append(sorted(p.fds));p.fds.clear();g.exitcode=a&255;u.emu_stop();return 0
  if n in (221,281):self.exec_attempts.append(n);raise AssertionError('exec forbidden in no-exec child')
  raise AssertionError(('unexpected syscall',p.pid,n,args))
 def summary(self):
  assert all(fd in self.parent.fds and self.parent.fds[fd]['desc'] is x[0] and self.parent.fds[fd]['flags']==x[1] for fd,x in self.borrowed.items())
  return dict(anonymous_mappings=self.anonymous_mappings,protection_changes=self.protection_changes,foreign_clone_PID_reuse_injected=self.pid_reused,clones=self.clone_events,waits=self.waits,reaper=self.reaper,child_exit=self.child.exit_status if self.child else None,child_alive=self.child.alive if self.child else None,parent_mask=self.parent.mask,parent_SIGCHLD=self.parent.actions[17].hex(),child_signal_ops=len(self.signal_ops),new_original_signal_handlers_executed=False,exec_attempts=self.exec_attempts,source_accesses=self.source_accesses,borrowed_FDs_unchanged=True,rights_all_closed=all(fd not in self.parent.fds for fd in self.rights),child_FDs_before_GRANT=self.child_FD_sets,kernel_exit_closes=self.exit_cleanup,files={p:bytes(n.data).hex() for p,n in self.nodes.items() if p.startswith('/tmp_wbshd/') and n.mode&0o170000==0o100000})
class Guest:
 def __init__(self,raw,process,base=0x30000000,copy_from=None):
  self.raw=raw;self.process=process;self.kernel=process.kernel;self.base=base;self.report=D.inspect(raw);self.errors=[];self.trace=[];self.exitcode=None;self.blocked=False;self.unloaded=False;self.u=U.Uc(U.UC_ARCH_ARM64,U.UC_MODE_ARM);self.stop=0x71000000
  if copy_from:
   for a,z,perms in copy_from.u.mem_regions():self.u.mem_map(a,z-a+1,perms);self.u.mem_write(a,bytes(copy_from.u.mem_read(a,z-a+1)))
   self.u.context_restore(copy_from.u.context_save())
  else:
   for seg in self.report['segments']:
    flags=seg['flags'];perms=(U.UC_PROT_READ if flags&4 else 0)|(U.UC_PROT_WRITE if flags&2 else 0)|(U.UC_PROT_EXEC if flags&1 else 0);self.u.mem_map(base+seg['va'],D.align(seg['memsz'],D.PAGE),perms)
    if seg['filesz']:self.u.mem_write(base+seg['va'],raw[seg['offset']:seg['offset']+seg['filesz']])
   for rel in self.report['runtime_relocations']:self.u.mem_write(base+rel['offset'],struct.pack('<Q',base+rel['addend']))
   self.u.mem_protect(base+3*D.PAGE,D.PAGE,U.UC_PROT_READ);self.u.mem_map(0x70000000,0x20000,U.UC_PROT_READ|U.UC_PROT_WRITE);self.u.mem_map(self.stop,4096,U.UC_PROT_READ|U.UC_PROT_EXEC);self.u.reg_write(A.UC_ARM64_REG_CPACR_EL1,3<<20)
  self.u.hook_add(U.UC_HOOK_INTR,self.interrupt)
 def interrupt(self,u,number,unused):
  try:
   assert number==2;n=u.reg_read(A.UC_ARM64_REG_X8);args=[u.reg_read(r) for r in REG];args=[v-(1<<64) if v>>63 else v for v in args];self.trace.append(n);value=self.kernel.syscall(self,n,args);u.reg_write(A.UC_ARM64_REG_X0,value&0xffffffffffffffff)
  except Blocked:self.blocked=True;u.emu_stop()
  except BaseException:self.errors.append(traceback.format_exc());u.emu_stop()
 def call(self,va):
  assert not self.unloaded
  for i in range(8):self.u.reg_write(getattr(A,'UC_ARM64_REG_X'+str(i)),0xdeadbeef00000000+i)
  self.u.reg_write(A.UC_ARM64_REG_SP,0x7001f000);self.u.reg_write(A.UC_ARM64_REG_X30,self.stop)
  self.u.emu_start(self.base+va,self.stop,count=100_000_000);assert not self.errors,self.errors;assert self.u.reg_read(A.UC_ARM64_REG_PC)==self.stop;v=self.u.reg_read(A.UC_ARM64_REG_X0)&0xffffffff;return v-(1<<32) if v>>31 else v
 def initialize(self):self.call(self.report['runtime_relocations'][0]['addend']);return self.status()
 def status(self):return (self.call(self.report['exports']['fx3_entry_state']['va']),self.call(self.report['exports']['fx3_entry_reason']['va']))
 def unload(self):
  for s in self.report['segments']:self.u.mem_unmap(self.base+s['va'],D.align(s['memsz'],D.PAGE))
  self.unloaded=True
 def drop_original_file_backing(self):
  for s in self.report['segments']:self.u.mem_unmap(self.base+s['va'],D.align(s['memsz'],D.PAGE))
 def run_child(self):
  assert self.process.pid==7001
  for _ in range(30):
   self.u.emu_start(self.u.reg_read(A.UC_ARM64_REG_PC),0,count=2_000_000)
   if self.exitcode is not None or self.blocked or self.errors:break
  assert not self.errors,self.errors;assert self.exitcode is not None or self.blocked;return self.exitcode
