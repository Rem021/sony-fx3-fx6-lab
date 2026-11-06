"""Own ARM64 observer with fake proc inode/PID-object lifetime providers.
No original code execution, target connection or real /proc reads.
The anchor refers to an object, separately from the numeric-pid index.
"""
from pathlib import Path
from hashlib import sha256
import struct,traceback,json,importlib.util
import unicorn as U
import unicorn.arm64_const as A
import candidate_build as D
H=Path(__file__).resolve().parent;B=H.parent
REG=[getattr(A,'UC_ARM64_REG_X'+str(n)) for n in range(6)]
def row(state='S',status=10752,pid=5001,parent=321,start=777,threads=1,comm='own collector'):
 values={n:'0' for n in range(4,53)};values.update({4:str(parent),20:str(threads),22:str(start),52:str(status)});values[8]='-1';values[18]='20'
 return f'{pid} ({comm}) {state} '.encode()+(' '.join(values[n] for n in range(4,53))+'\n').encode()
class ProcObject:
 def __init__(self,name,phases,exit_status=10752):self.name=name;self.phases=phases;self.exit_status=exit_status;self.pid=5001;self.parent=321;self.start=777;self.threads=1;self.permitted=True
class Kernel:
 def __init__(self,raw,fault=None,status=10752):
  self.raw=raw;self.fault=fault;self.phase=0;self.sleeps=0;self.lookups=[];self.meta_calls=[];self.reads=[];self.closes=[];self.events=[];self.status=None;self.waits=[];self.new=[];self.nextfd=54
  self.original=ProcObject('original object A',['S','Z','GONE'],status);self.foreign=ProcObject('foreign object B',['Z'],10752);self.numeric_index={5001:self.original};self.anchor_object=self.original
  self.host={fd:dict(kind='borrowed',name=str(fd)) for fd in [0,1,2,7]};self.host_before=dict(self.host);self.fds=dict(self.host);self.fds[53]=dict(kind='anchor',object=self.anchor_object,inode=7001);self.before_exit=None
  if fault=='gone-before-evidence':self.original.phases=['GONE']
  if fault=='filtered-zero':self.original.permitted=False
  if fault=='live-zero':self.original.phases=['S'];self.original.exit_status=0
  if fault=='zombie-only':self.original.phases=['Z']
  if fault=='bad-pid':self.original.pid=5002
  if fault=='bad-parent':self.original.parent=322
  if fault=='bad-start':self.original.start=778
  if fault=='multi-thread':self.original.threads=2
  if fault=='wrong-anchor-same-pid-and-start':self.anchor_object=self.foreign;self.foreign.phases=['S','Z','GONE'];self.fds[53]['object']=self.foreign
 def state(self,obj):return obj.phases[min(self.phase,len(obj.phases)-1)]
 def stat_bytes(self,obj):
  status=obj.exit_status if obj.permitted else 0
  s=row(self.state(obj),status,obj.pid,obj.parent,obj.start,obj.threads,comm='a) S 9\n(b' if self.fault=='complex-comm' else 'own collector')
  if self.fault=='truncated-record':s=s[:-3]
  if self.fault=='extra-field':s=s[:-1]+b' 0\n'
  if self.fault=='exit-overflow':s=row('Z',18446744073709551616)
  if self.fault=='negative-exit':s=row('Z',-10752)
  if self.fault=='huge-record':s=b'X'*4096
  return s
 def syscall(self,g,n,args):
  u=g.u;a,b,c,d,e,f=args
  def text(at):
   buf=bytearray()
   for i in range(32):
    x=u.mem_read(at+i,1)[0]
    if not x:return buf.decode()
    buf.append(x)
   raise AssertionError('unexpected path')
  if n in (174,175):return 0
  if n==80:
   if a not in self.fds:return -9
   desc=self.fds[a];inode=desc.get('inode',8000+a);mode=0o40500 if desc['kind']=='anchor' else 0o100444;uid=0
   if desc['kind']=='anchor' and self.fault=='anchor-not-directory':mode=0o100600
   if desc['kind']=='anchor' and self.fault=='anchor-UID':uid=501
   if desc['kind']=='anchor' and self.fault=='anchor-replaced' and self.phase>=1:inode+=1
   if desc['kind']=='stat' and self.fault=='stat-inode-changed':
    desc['meta_count']=desc.get('meta_count',0)+1
    if desc['meta_count']>1:inode+=1
   out=bytearray(128);struct.pack_into('<QQIIII',out,0,9,inode,mode,1,uid,0);u.mem_write(b,bytes(out));self.meta_calls.append(dict(fd=a,kind=desc['kind'],inode=inode));return 0
  if n==44:
   data=[0]*15;data[0]=0x9fa0
   if self.fault=='wrong-filesystem':data[0]=0x01021994
   u.mem_write(b,struct.pack('<15Q',*data));return 0
  if n==56:
   assert a==53 and text(b)=='stat' and c==0xa0000 and (d,e,f)==(0,0,0)
   obj=self.fds[a]['object'];state=self.state(obj);self.lookups.append(dict(relative_anchor_fd=a,object=obj.name,phase=self.phase,state=state,numeric_index_object=self.numeric_index[5001].name))
   if self.fault=='post-sentinel-EACCES' and state=='GONE':return -13
   if state=='GONE':return -3 if self.fault=='gone-ESRCH' else -2
   fd=self.nextfd;self.nextfd+=1;self.new.append(fd);self.fds[fd]=dict(kind='stat',object=obj,data=self.stat_bytes(obj),pos=0,inode=8000+fd);return fd
  if n==63:
   desc=self.fds[a];assert desc['kind']=='stat';obj=desc['object']
   if self.fault=='read-error':return -5
   data=desc['data'][desc['pos']:desc['pos']+min(c,17 if self.fault=='short-chunks' else c)];desc['pos']+=len(data);u.mem_write(b,data);self.reads.append(dict(fd=a,object=obj.name,bytes=len(data)));return len(data)
  if n==57:
   assert a in self.fds;kind=self.fds[a]['kind'];self.closes.append(dict(fd=a,kind=kind));del self.fds[a]
   if self.fault=='anchor-close-error' and a==53:return -5
   if self.fault=='stat-close-error' and kind=='stat':return -5
   return 0
  if n==101:
   assert tuple(struct.unpack('<qq',u.mem_read(a,16)))==(0,10000000);self.sleeps+=1;self.phase+=1
   if self.fault in ('numeric-reuse-after-exit','numeric-reuse-before-evidence'):
    self.numeric_index[5001]=self.foreign
    if self.fault=='numeric-reuse-before-evidence':self.original.phases=['GONE']
    self.events.append(dict(event='same numeric PID now indexes B',original_anchor_object=self.fds[53]['object'].name))
   return 0
  if n==93:
   self.status=a&255;self.before_exit=sorted(self.fds);g.u.emu_stop();return 0
  if n==260:self.waits.append(args);raise AssertionError('numeric wait must not be used')
  raise AssertionError(('unexpected observer syscall',n,args))
 def summary(self,g):
  assert self.host==self.host_before
  return dict(fault=self.fault,result=self.status,state=g.state(),collector_kernel_raw_status=self.original.exit_status,filtered=not self.original.permitted,
    anchor_origin=self.anchor_object.name,lookups=self.lookups,closes=self.closes,waits=self.waits,events=self.events,
    host_borrowed_FDs_unchanged=True,remaining_before_wrapper_exit=self.before_exit,new_stat_FDs_all_closed=all(n not in self.fds for n in self.new),
    all_lookups_relative_to_original_object=all(x['object']==self.anchor_object.name for x in self.lookups),
    no_numeric_pid_path_lookup_or_wait=True)
class Guest:
 def __init__(self,k):
  self.k=k;self.u=U.Uc(U.UC_ARCH_ARM64,U.UC_MODE_ARM);self.errors=[]
  for s in D.read_executable(k.raw):
   perm=(U.UC_PROT_READ if s['flags']&4 else 0)|(U.UC_PROT_WRITE if s['flags']&2 else 0)|(U.UC_PROT_EXEC if s['flags']&1 else 0);self.u.mem_map(s['va'],D.align(s['memsz'],D.PAGE),perm)
   if s['filesz']:self.u.mem_write(s['va'],k.raw[s['offset']:s['offset']+s['filesz']])
  self.u.mem_map(0x70000000,0x20000,U.UC_PROT_READ|U.UC_PROT_WRITE);self.u.reg_write(A.UC_ARM64_REG_SP,0x7001f000);self.u.reg_write(A.UC_ARM64_REG_CPACR_EL1,3<<20);self.u.hook_add(U.UC_HOOK_INTR,self.interrupt)
 def interrupt(self,u,no,_):
  try:
   assert no==2;n=u.reg_read(A.UC_ARM64_REG_X8);a=[u.reg_read(r) for r in REG];a=[v-(1<<64) if v>>63 else v for v in a];v=self.k.syscall(self,n,a);u.reg_write(A.UC_ARM64_REG_X0,v&0xffffffffffffffff)
  except BaseException:self.errors.append(traceback.format_exc());u.emu_stop()
 def run(self):
  self.u.emu_start(D.HEADER.unpack_from(self.k.raw)[4],0,count=8_000_000);assert not self.errors,self.errors;assert self.k.status is not None
 def state(self):return struct.unpack('<I',self.u.mem_read(D.read_executable(self.k.raw)[-1]['va'],4))[0]
def case(raw,fault=None,status=10752):
 k=Kernel(raw,fault,status);g=Guest(k);g.run();return k.summary(g)
def producer(raw,fault=None,pause_after_anchor=False,return_live=False):
 p=B/'stage237-isolated-collector-child-domain/model_collector.py';spec=importlib.util.spec_from_file_location('collector238_pair',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 class ProducerKernel(m.Kernel):
  def __init__(self):
   super().__init__(raw,fault);self.collector.fds[53]=dict(kind='outer-private-channel');self.sent_anchors=[]
  def syscall(self,g,n,args):
   a,b,c,d,e,f=args;p=g.p;u=g.u
   if n==56 and p is self.collector and bytes(u.mem_read(b,11))==b'/proc/self\0':
    assert (a,c)==(-100,0x90000)
    if fault=='anchor-open-error':return -2
    return p.fd(dict(kind='self-proc-anchor',object=p))
   if n==211 and p is self.collector and a==53:
    if fault=='anchor-send-error':return -5
    _,_,iov,ilen,ctl,size,_=struct.unpack('<QI4xQQQQI4x',u.mem_read(b,56));ptr,length=struct.unpack('<QQ',u.mem_read(iov,16));assert length==256 and ilen==1 and size==24
    rawctl=bytes(u.mem_read(ctl,size));assert struct.unpack_from('<QII',rawctl)==(20,1,1);fd=struct.unpack_from('<I',rawctl,16)[0];row=p.fds[fd];assert row['kind']=='self-proc-anchor' and row['object'] is p
    hello=bytes(u.mem_read(ptr,256));assert struct.unpack_from('<III',hello,20)==(3,p.pid,0)
    self.sent_anchors.append(dict(sender_pid=p.pid,receiver_fd=53,source_fd=fd,object_identity='same collector object as sender',not_numeric_reopen=True,hello_sha256=sha256(hello).hexdigest()))
    if pause_after_anchor:g.paused=True;u.emu_stop()
    return 256
   return super().syscall(g,n,args)
 k=ProducerKernel();g=m.Guest(k,k.collector);g.run()
 if return_live:return k,g
 r=k.summary();r['self_proc_anchor_transfers']=k.sent_anchors;return r

class LinkedProcObject:
 """proc descriptor references exactly the running producer's process object."""
 def __init__(self,process):self.process=process;self.name='same running collector object A';self.start=777;self.threads=1;self.permitted=True
 @property
 def pid(self):return self.process.pid
 @property
 def parent(self):return self.process.parent
 @property
 def exit_status(self):return self.process.status or 0
def paired(observer_raw,collector_raw,fault=None,observer_fault=None):
 pk,pg=producer(collector_raw,fault,pause_after_anchor=True,return_live=True)
 assert len(pk.sent_anchors)==1 and pk.collector.alive and pg.paused
 class PairedKernel(Kernel):
  def __init__(self):
   super().__init__(observer_raw,observer_fault);self.original=LinkedProcObject(pk.collector);self.anchor_object=self.original;self.fds[53]['object']=self.original;self.numeric_index[5001]=self.original
  def state(self,obj):
   if isinstance(obj,LinkedProcObject):return 'GONE' if obj.process.reaped else ('S' if obj.process.alive else 'Z')
   return super().state(obj)
  def syscall(self,g,n,args):
   if n==101:
    if pk.collector.alive:pg.paused=False;pg.run()
    elif self.phase>=1:pk.collector.reaped=True;self.events.append(dict(event='explicit fake Sony parent reaps collector',status=pk.collector.status))
   return super().syscall(g,n,args)
 k=PairedKernel();g=Guest(k);g.run();r=k.summary(g);r['producer']=pk.summary();r['self_proc_anchor_transfers']=pk.sent_anchors;r['same_live_process_object_used_by_both_own_machines']=True;return r
