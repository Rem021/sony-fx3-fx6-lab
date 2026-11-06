"""Own C receiver/collector/worker in explicit fake Linux, no original code.
Descriptor transfer preserves the producer's running process object. Faults
can additionally declare unsupported malformed kernel control-buffer output;
those may retain unidentified rights and must remain UNKNOWN, not clean.
"""
from pathlib import Path
from hashlib import sha256
from collections import deque
import importlib.util,sys,struct,json,zlib
import receiver_build as D
H=Path(__file__).resolve().parent;B=H.parent
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=sys.modules.get('candidate_build');sys.modules['candidate_build']=module('builder238_receiver',B/'stage238-proc-anchor-and-nonzero-exit-sentinel/candidate_build.py')
try:M=module('observer238_receiver',B/'stage238-proc-anchor-and-nonzero-exit-sentinel/model_observer.py')
finally:
 if old is None:sys.modules.pop('candidate_build',None)
 else:sys.modules['candidate_build']=old
def cmsg(kind,p,pad=True):
 x=struct.pack('<QII',16+len(p),1,kind)+p;return x+bytes((-len(x))%8) if pad else x
class ParentKernel(M.Kernel):
 def __init__(self,raw,collector_raw,fault=None,producer_fault=None):
  super().__init__(raw,None);self.clock=1_000_000_000;self.case_fault=fault;self.ack=[];self.received=[];self.hello_consumed=False;self.receiver_errors=[];self.nextfd=80;self.observe_started=False
  self.pk,self.pg=M.producer(collector_raw,producer_fault,pause_after_anchor=True,return_live=True)
  assert self.pk.collector.alive and self.pg.paused and len(self.pk.sent_anchors)==1
  u=self.pg.u;address=u.reg_read(M.A.UC_ARM64_REG_X1);_,_,iov,_,control,clen,_=struct.unpack('<QI4xQQQQI4x',u.mem_read(address,56));ptr,size=struct.unpack('<QQ',u.mem_read(iov,16));self.hello=bytes(u.mem_read(ptr,size));fd=struct.unpack_from('<I',u.mem_read(control,clen),16)[0];assert self.pk.collector.fds[fd]['object'] is self.pk.collector
  self.original=M.LinkedProcObject(self.pk.collector);self.anchor_object=self.original;self.numeric_index={5001:self.original};self.fds[53]=dict(kind='channel',cloexec=1)
  if fault=='foreign-origin-same-pid':
   self.pk.terminate(self.pk.collector,9,'explicit A death before foreign HELLO delivery');self.pk.collector.reaped=True
   self.original=M.ProcObject('foreign B reused PID after A detached',['S','Z','GONE'],10752);self.original.start=888;self.anchor_object=self.original
   self.events.append(dict(event='discard A HELLO; after A death/reap receive forged B HELLO through assumed inherited endpoint',A_dead_before_B_active=True,B_distinct_start_tick=888,private_endpoint_inherited_by_foreign_before_A_death=True,not_a_swap_of_genuine_SCM_RIGHTS=True,not_actual_camera_observation=True))
  self.queue=deque();base=self.pk.syscall
  def producer_syscall(g,n,args):
   a,b,c,d,e,f=args;u=g.u
   if n==212 and g.p is self.pk.collector and a==53:
    if not self.queue:return -11
    data=self.queue.popleft();_,_,iov,ilen,ctl,capacity,_=struct.unpack('<QI4xQQQQI4x',u.mem_read(b,56));ptr,size=struct.unpack('<QQ',u.mem_read(iov,16));assert ilen==1 and size==256
    creds=cmsg(2,struct.pack('<III',9999 if fault=='ACK-wrong-parent' else 321,0,0));assert len(creds)<=capacity;u.mem_write(ptr,data);u.mem_write(ctl,creds);u.mem_write(b+40,struct.pack('<Q',len(creds)));u.mem_write(b+48,bytes(4));return 256
   return base(g,n,args)
  self.pk.syscall=producer_syscall
 def state(self,obj):
  if isinstance(obj,M.LinkedProcObject):return 'GONE' if obj.process.reaped else ('S' if obj.process.alive else 'Z')
  return super().state(obj)
 def descriptor(self,obj=None):
  fd=self.nextfd;self.nextfd+=1;self.fds[fd]=dict(kind='anchor',object=obj or self.original,inode=7001+len(self.received),cloexec=0 if self.case_fault=='received-no-cloexec' else 1);self.received.append(fd);return fd
 def syscall(self,g,n,args):
  a,b,c,d,e,f=args;u=g.u;fault=self.case_fault
  if n==172:return 321
  if n==25:
   assert b==1 and (c,d,e,f)==(0,0,0,0)
   if a not in self.fds:return -9
   return 0 if a==53 and fault=='channel-no-cloexec' else self.fds[a].get('cloexec',0)
  if n==80 and self.fds.get(a,{}).get('kind')=='channel':
   out=bytearray(128);struct.pack_into('<QQIIII',out,0,3,9001,0o140600,1,0,0);u.mem_write(b,bytes(out));return 0
  if n==209:
   assert a==53 and b==1
   if c==3:u.mem_write(d,struct.pack('<I',1 if fault=='socket-stream' else 2));u.mem_write(e,struct.pack('<I',4));return 0
   if c==16:u.mem_write(d,struct.pack('<I',0 if fault=='no-passcred' else 1));u.mem_write(e,struct.pack('<I',4));return 0
   if c==17:u.mem_write(d,struct.pack('<III',999 if fault=='bad-peer-creator' else 321,0,0));u.mem_write(e,struct.pack('<I',12));return 0
   raise AssertionError('unexpected socket profile')
  if n==204:
   assert a==53;u.mem_write(b,struct.pack('<H',1));u.mem_write(c,struct.pack('<I',3 if fault=='named-socket' else 2));return 0
  if n==113:
   self.clock=max(self.clock,self.pk.clock);self.clock+=1000;self.pk.clock=self.clock;u.mem_write(b,struct.pack('<qq',self.clock//10**9,self.clock%10**9));return 0
  if n==212:
   assert a==53 and c==0x40000040
   if self.hello_consumed or fault=='no-HELLO':return -11
   self.hello_consumed=True
   _,_,iov,ilen,control,capacity,_=struct.unpack('<QI4xQQQQI4x',u.mem_read(b,56));ptr,size=struct.unpack('<QQ',u.mem_read(iov,16));assert ilen==1 and size==256 and capacity==4096
   data=bytearray(self.hello)
   if fault=='wrong-payload':data[32]^=1
   if fault=='old-HELLO-v1':
    data[:16]=b'FX3ISOCOLLECT1'.ljust(16,b'\0');struct.pack_into('<I',data,16,1);data[80:96]=bytes(16);struct.pack_into('<I',data,252,zlib.crc32(data[:252]))
   if fault=='short-payload':data=data[:120]
   sender=9999 if fault=='wrong-credential-PID' else 5001;uid=501 if fault=='wrong-UID' else 0;gid=501 if fault=='wrong-GID' else 0
   cred=cmsg(2,struct.pack('<III',sender,uid,gid));rights=[]
   if fault!='no-rights':
    total=253 if fault=='253-rights' else (2 if fault=='two-rights' else 1)
    rights=[self.descriptor() for _ in range(total)]
   rights_msg=cmsg(1,b''.join(struct.pack('<I',fd) for fd in rights),pad=fault!='unpadded-last-rights') if rights else b''
   if fault=='duplicate-receiver-number':rights_msg=cmsg(1,struct.pack('<II',rights[0],rights[0]))
   if fault=='no-credentials':ctl=rights_msg
   elif fault=='duplicate-credentials':ctl=cred+cred+rights_msg
   elif fault=='reversed-control-order':ctl=rights_msg+cred
   elif fault=='malformed-kernel-header':ctl=struct.pack('<QII',8,1,1)+struct.pack('<I',rights[0])+bytes(4)
   elif fault=='header-copy-fault-after-FD-install':ctl=b'';u.mem_write(control+16,struct.pack('<I',rights[0]))
   elif fault=='header-copy-fault-without-CTRUNC':ctl=cred;u.mem_write(control+len(cred)+16,struct.pack('<I',rights[0]))
   elif fault=='negative-after-installed-rights':ctl=cred+rights_msg
   else:ctl=cred+rights_msg
   flags=0x20 if fault=='payload-truncated' else (8 if fault in ('control-truncated','header-copy-fault-after-FD-install') else 0)
   assert len(ctl)<=capacity;u.mem_write(ptr,bytes(data));u.mem_write(control,ctl);u.mem_write(b+40,struct.pack('<Q',len(ctl)));u.mem_write(b+48,struct.pack('<I',flags));self.events.append(dict(event='kernel installs received rights',FDs=rights,control_bytes=len(ctl),unsupported_kernel_schema=fault=='malformed-kernel-header'))
   if fault=='late-before-ACK':self.clock+=3_000_000_000
   return -14 if fault=='negative-after-installed-rights' else len(data)
  if n==211:
   assert a==53 and c==0x4040;_,_,iov,ilen,control,clen,_=struct.unpack('<QI4xQQQQI4x',u.mem_read(b,56));ptr,size=struct.unpack('<QQ',u.mem_read(iov,16));assert ilen==1 and size==256 and not control and not clen
   data=bytes(u.mem_read(ptr,size));self.ack.append(dict(type=struct.unpack_from('<I',data,20)[0],sha256=sha256(data).hexdigest(),collector_worker_created_already=self.pk.worker is not None))
   if fault=='ACK-send-error':return -5
   if fault=='ACK-corrupt':data=data[:32]+bytes([data[32]^1])+data[33:]
   self.queue.append(data)
   if fault=='late-after-ACK':self.clock+=3_000_000_000;self.pk.clock=self.clock
   return 256
  if n==56:
   assert a in self.fds and self.fds[a]['kind']=='anchor'
   obj=self.fds[a]['object'];path=bytes(u.mem_read(b,5));assert path==b'stat\0' and c==0xa0000
   state=self.state(obj);self.lookups.append(dict(relative_anchor_fd=a,object=obj.name,phase=self.phase,state=state,numeric_index_object=self.numeric_index[5001].name))
   if state=='GONE':return -2
   fd=self.nextfd;self.nextfd+=1;self.new.append(fd);self.fds[fd]=dict(kind='stat',object=obj,data=self.stat_bytes(obj),pos=0,inode=8000+fd);return fd
  if n==101:
   assert tuple(struct.unpack('<qq',u.mem_read(a,16)))==(0,10000000);self.sleeps+=1;self.phase+=1;self.clock+=10000000;self.pk.clock=max(self.pk.clock,self.clock)
   if self.ack and self.pk.collector.alive:self.pg.paused=False;self.pg.run();self.clock=max(self.clock,self.pk.clock)
   elif self.ack and not self.pk.collector.alive and self.phase>=2:self.pk.collector.reaped=True
   return 0
  if n==57:
   kind=self.fds.get(a,{}).get('kind');r=super().syscall(g,n,args)
   if kind=='anchor' and fault=='received-close-error':return -5
   if kind=='channel' and fault=='channel-close-error':return -5
   return r
  return super().syscall(g,n,args)
 def finish(self,g):
  r=self.summary(g);r.update(parent_sleeps=self.sleeps,ack=self.ack,received_FDs=self.received,received_remaining=[fd for fd in self.received if fd in self.fds],receiver_state=g.receiver_state(),producer=self.pk.summary(),self_proc_anchor_transfers=self.pk.sent_anchors,
     explicit_incomplete_control_cleanup=any(fd in self.fds for fd in self.received),own_C_ACK_precedes_inner_worker=all(not a['collector_worker_created_already'] for a in self.ack),foreign_origin_boundary=self.case_fault=='foreign-origin-same-pid')
  return r
class Guest(M.Guest):
 def __init__(self,k,object_path):
  super().__init__(k);obj=D.Object(object_path.read_bytes(),'own parent');self.variables={x['name']:x['value'] for x in obj.symbols if x['name'] in ('receiver_state','observer_state')};assert len(self.variables)==2
 def state(self):return self.receiver_state()
 def receiver_state(self):return struct.unpack('<I',self.u.mem_read(D.read_executable(self.k.raw)[-1]['va']+self.variables['receiver_state'],4))[0]
def case(parent_raw,collector_raw,object_path,fault=None,producer_fault=None):
 k=ParentKernel(parent_raw,collector_raw,fault,producer_fault);g=Guest(k,object_path);g.run();return k.finish(g)

def drive_rejected_peer(parent_raw,collector_raw,object_path,fault):
 k=ParentKernel(parent_raw,collector_raw,fault);g=Guest(k,object_path);g.run();before=k.finish(g);k.pg.paused=False;k.pg.run();before['producer_after_parent_return']=k.pk.summary();return before
