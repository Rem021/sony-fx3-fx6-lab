from pathlib import Path
import tempfile,json,struct
from gate_input104_v1 import KernelObserver
R=Path(__file__).resolve().parent;proof=json.loads((R/'ap104-observer-original-proof-v1.json').read_text())
Q=0xffffffc011234000;TASK=0xffffffc012340000;FP=0xffffff8009001000;TP=0x7f12340000;STATUS=0x7f12348000
class Sys:
 def read(self,name):return TASK if name=='SP_EL0'else TP
class Gate:
 def __init__(self):self.mem={};self.regs=[0]*33;self.commands=[];self.owner=0;self.label='';self.points={}
 def connect(self):pass
 def virtual_read(self,a,n):
  if a in self.mem:return self.mem[a][:n]
  if a==Q:
   b=bytearray(64);b[0]=8;struct.pack_into('<Q',b,48,self.owner);return bytes(b)
  if a==TASK+0x388:return struct.pack('<I',275)
  if a==TASK+0x538:return b'MPGRM_GPE0\0'.ljust(16,b'\0')
  if a==FP+0x80:return struct.pack('<QII',0xffffff80004be818,0,0x82)
  if a==STATUS:return bytes(n)
  return None
 def packet(self,p):
  self.commands.append(p)
  if p.startswith(('Z1,','z1,')):return 'OK'
  if p=='g':return struct.pack('<33Q',*self.regs).hex()+struct.pack('<I',5 if self.label.startswith(('dynamic_','completion_alloc','first_unfetched'))else 0).hex()
  if p=='s':
   if self.label=='dynamic_owner_claim':self.owner=self.regs[0]
   if self.label in ['dynamic_owner_release','dynamic_owner_pending_release']:self.owner=0
   if self.label=='first_unfetched_return':self.regs[0]=(-1018)&0xffffffff
   self.regs[32]+=4;return 'T05thread:03;'
  raise AssertionError('Unexpected probe/control packet '+p)
class QMP:
 def __init__(self):self.commands=[]
 def __call__(self,p,*args):self.commands.append(p);assert p in ['query-status','cont'];return {'return':{'status':'debug'}}

with tempfile.TemporaryDirectory(prefix='fx3-gate104-')as td:
 root=Path(td);(root/'ap104-observer-original-proof-v1.json').write_text(json.dumps(proof));run=root/'runs'/'owner';run.mkdir(parents=True);(run/'serial.log').write_text('');g=Gate();qmp=QMP();o=KernelObserver(run,g,qmp,{'kernel_points':[]});o.sysregs=Sys();base=0xffffff80004be000
 for p in proof['uipc_points']:g.mem[base+p['offset']]=bytes.fromhex(p['raw'])
 o.install_uipc(base)
 def hit(label):
  p=next(x for x in proof['uipc_points']if x['label']==label);g.label=label;g.regs=[0]*33;g.regs[0]=0x8261c0;g.regs[3]=Q;g.regs[19]=0x2a if label=='dynamic_owner_claim'else 0x4a;g.regs[21]=Q;g.regs[23]=Q;g.regs[24]=0x808261c0;g.regs[25]=0x808261c0;g.regs[29]=FP;g.regs[31]=FP-128;g.regs[32]=base+p['offset'];assert o.poll();return o.records[-1]
 a=hit('dynamic_owner_claim');assert a['new_observation_epoch']['observation_epoch']==1 and a['thread']['native_task_pid']==275
 b=hit('dynamic_owner_release');assert b['released_observation_epoch']['observation_epoch']==1 and not o.owner_epochs
 c=hit('dynamic_owner_claim');assert c['new_observation_epoch']['observation_epoch']==2
 hit('dynamic_owner_pending_release');hit('completion_alloc_owner_read');before=len(qmp.commands);hit('first_unfetched_return');assert o.first_unfetched['actual_original_error_w0']==-1018 and 'cont'not in qmp.commands[before:]
 o.close();assert o.removed and all(x['same_original_runtime_word']for x in o.original_words_unchanged);assert not any(p in ['?','qC']or p.startswith(('Hg','Hc','M','G','P'))for p in g.commands)
 run=root/'runs'/'user';run.mkdir(parents=True);(run/'serial.log').write_text(f'FX3_GPE104_COMPLETE_ENTER tid=275 tpidr={hex(TP)}\n');g=Gate();qmp=QMP();o=KernelObserver(run,g,qmp,{'kernel_points':[]});o.sysregs=Sys();base=0x7f40000000;o.module_bases['gpe']=base
 for p in proof['user_gpe_points']:g.mem[base+p['offset']]=bytes.fromhex(p['raw'])
 o._add(base,proof['user_gpe_points'])
 def user(label,sp,x0,x1=0,x2=0,lr=0):
  p=next(x for x in proof['user_gpe_points']if x['label']==label);g.label=label;g.regs=[0]*33;g.regs[0]=x0;g.regs[1]=x1;g.regs[2]=x2;g.regs[30]=lr;g.regs[31]=sp;g.regs[32]=base+p['offset'];assert o.poll();return o.records[-1]
 a=user('original_Main_SyncCallback_enter',0x7f22220000,123,0x808261c0);assert a['thread']['mapped_user_tid']==275
 b=user('original_SendDrawComp_enter',0x7f2221ffe0,0x808261c0,STATUS,4,base+0xa12c);assert b['call_path']=='original_Main_SyncCallback'and b['status_raw']=='00000000'
 c=user('original_shared_Send_return',0x7f2221ffe0,1);assert c['call_enter_index']==b['index']and c['completion_bool_result']==1
 d=user('original_Main_SyncCallback_return',0x7f22220000,0);assert d['call_enter_index']==a['index']and d['return_w0']==0;o.close()
print('AP104_NATIVE_STOP_CPU_OWNER_EPOCH_REUSE_CLEAR_FIRST_ERROR_USER_CALL_PAIRING_READONLY_PASS')
