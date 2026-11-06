"""Exercise real socket readiness for fast debug dispatch and stale packets."""
from pathlib import Path
import tempfile,json,socket,select,time
from check_gate104_v3 import Gate,Sys,KernelObserver,proof,Q,TASK,FP
class QMP:
 def __init__(self,states):self.states=list(states);self.commands=[]
 def __call__(self,p,*a):
  self.commands.append(p)
  if p=='cont':return {'return':{}}
  assert p=='query-status';state=self.states.pop(0)if len(self.states)>1 else self.states[0];return {'return':{'status':state}}
with tempfile.TemporaryDirectory(prefix='fx3-wait104-')as td:
 root=Path(td);(root/'ap104-observer-original-proof-v1.json').write_text(json.dumps(proof))
 for name,states,ready,expected in [('ready',['running','debug'],True,True),('idle',['running'],False,False),('stale',['running'],True,False)]:
  run=root/'runs'/name;run.mkdir(parents=True);(run/'serial.log').write_text('');g=Gate();qm=QMP(states);o=KernelObserver(run,g,qm,{'kernel_points':[]});o.sysregs=Sys();base=0xffffff80004be000
  for p in proof['uipc_points']:g.mem[base+p['offset']]=bytes.fromhex(p['raw'])
  o.install_uipc(base);p=next(x for x in proof['uipc_points']if x['label']=='dynamic_owner_claim');g.label=p['label'];g.regs=[0]*33;g.regs[0]=0x8261c0;g.regs[3]=Q;g.regs[19]=0x2a;g.regs[29]=FP;g.regs[31]=FP-128;g.regs[32]=base+p['offset']
  a,b=socket.socketpair();g.sock=a;packet=g.packet
  def wrapped(s):
   if s=='qqemu.PhyMemMode':g.commands.append(s);a.recv(4096);return '1'
   return packet(s)
  g.packet=wrapped
  if ready:b.sendall(b'$T05thread:03;#00')
  start=time.monotonic();assert o.poll()is expected;elapsed=time.monotonic()-start
  if expected:assert len(o.records)==1 and o.records[0]['new_observation_epoch']['observation_epoch']==1 and 'cont'in qm.commands
  else:assert not o.records and 'cont'not in qm.commands
  if name=='stale':assert 'qqemu.PhyMemMode'in g.commands and not select.select([a],[],[],0)[0]
  o.close();a.close();b.close();print(name,'elapsed',round(elapsed,4))
print('AP104_NATIVE_STOP_SOCKET_READY_IDLE_STALE_READONLY_DISPATCH_PASS')
