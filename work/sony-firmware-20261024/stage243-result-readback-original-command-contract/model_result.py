"""Own ARM64 + explicit shared-VFS/process model; native GET is NOT run."""
from pathlib import Path
import importlib.util,json
H=Path(__file__).resolve().parent;B=H.parent
s=importlib.util.spec_from_file_location('own242_for_result',B/'stage242-DT-INIT-preparation-and-cross-load-claim/model_entry.py');M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
RESULT=M.CLAIM+'/entry.local-result-v1.bin'
class Kernel(M.Kernel):
 def __init__(self,*args,result_fault=None,**kwargs):
  super().__init__(*args,**kwargs);self.result_fault=result_fault;self.result_phase=False;self.result_events=[]
 def syscall(self,g,n,args):
  p=g.p;u=g.u;a,b,c,d,e,f=args;fault=self.result_fault
  def cstr(at):
   out=bytearray()
   for i in range(512):
    ch=u.mem_read(at+i,1)[0]
    if not ch:return out.decode()
    out.append(ch)
   raise AssertionError('unterminated result path')
  def file(fd):return p.fds.get(fd,{}).get('kind')=='vfs'
  if n==56 and file(a) and p.fds[a]['node'].path==M.CLAIM and cstr(b)=='entry.local-result-v1.bin':
   self.result_phase=True;self.result_events.append(dict(op='open',flags=c,mode=d))
   assert c&3==2 and c&0x20000 and c&0x80000 and c&0xc0==0xc0 and d==0o600
   if fault=='open':return -13
   if fault=='existing':self.fs.nodes[RESULT]=M.Node(RESULT,0o100600,b'older unrelated record',True)
   if RESULT in self.fs.nodes:return -17
   node=M.Node(RESULT,0o100600,ram=True);self.fs.nodes[RESULT]=node
   return p.fd(dict(kind='vfs',node=node,pos=0,flags=c,cloexec=1))
  if n in [63,64,82,57] and file(a) and p.fds[a]['node'].path==RESULT:
   row=p.fds[a];node=row['node']
   if n==64:
    size=120 if fault=='short-write' else c;assert c==256 and row['pos']==0
    node.data[:]=bytes(u.mem_read(b,size));row['pos']=size;node.gen+=1;self.result_events.append(dict(op='write',bytes=size));return size
   if n==82 and fault=='fsync':return -5
   if n==63 and fault=='readback':
    count=super().syscall(g,n,args)
    if count>0:u.mem_write(b,b'\xff')
    return count
   if n==57:
    result=super().syscall(g,n,args);self.result_events.append(dict(op='close',fd=a))
    return -5 if fault=='close' else result
  if n==57 and file(a) and self.result_phase:
   path=p.fds[a]['node'].path;result=super().syscall(g,n,args)
   if path==M.CLAIM and fault=='owner-close':return -5
   if path==M.ROOT:
    if fault=='root-close':return -5
    if fault=='expire-after-close':self.clock+=61_000_000_000
   return result
  return super().syscall(g,n,args)
 def summary(self,g):
  r=super().summary(g);r.update(result_fault=self.result_fault,result_events=self.result_events,result_record_hex=bytes(self.fs.nodes[RESULT].data).hex() if RESULT in self.fs.nodes else None,native_GET_or_USB_transport_executed=False);return r
def case(raw,im,**kwargs):
 base=kwargs.pop('base',0x30000000);k=Kernel(raw,im,**kwargs);g=M.Guest(k,k.root,base=base);g.run();return k,g,k.summary(g)
