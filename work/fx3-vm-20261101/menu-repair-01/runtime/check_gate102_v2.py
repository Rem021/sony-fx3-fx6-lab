import socket,threading
from pathlib import Path
from gate_input102_v2 import InputGate, KernelObserver

def packet(body):
 raw=body.encode();return b'$'+raw+b'#'+f'{sum(raw)%256:02x}'.encode()

def run_case(expect,action):
 a,b=socket.socketpair();a.settimeout(2);seen=[];errors=[]
 def server():
  try:
   for wanted,responses in expect:
    while b.recv(1)!=b'$':pass
    raw=bytearray()
    while True:
     c=b.recv(1)
     if c==b'#':break
     raw.extend(c)
    b.recv(2);seen.append(raw.decode());assert raw.decode()==wanted,(raw,wanted)
    b.sendall(b'+'+b''.join(packet(v) for v in responses))
    for response in responses:assert b.recv(1)==b'+'
  except BaseException as e:errors.append(e)
  finally:b.close()
 t=threading.Thread(target=server);t.start();g=InputGate(Path('.'),delete_key=0x1f8);g.sock=a
 try:action(g)
 finally:a.close();t.join(3)
 assert not t.is_alive() and not errors,errors
 return seen

def check(g):
 assert g.virtual_read(0xffffff8000001000,4)==bytes.fromhex('fd7bbaa9')
 assert g.packet('qC')=='QC2'
 assert g.packet('g')=='00'*264
 assert list(g.debug_stops)==['T02thread:2;']
 assert g.packet('s')=='T05thread:2;'
 assert g.virtual_read(0xffffff8000002000,4) is None
seen=run_case([('Qqemu.PhyMemMode:0',['OK']),('mffffff8000001000,4',['fd7bbaa9']),('Qqemu.PhyMemMode:1',['OK']),('qC',['QC2']),('g',['T02thread:2;','00'*264]),('s',['T05thread:2;']),('Qqemu.PhyMemMode:0',['OK']),('mffffff8000002000,4',['E01']),('Qqemu.PhyMemMode:1',['OK'])],check)
assert not any(x.startswith(('M','G','P')) for x in seen)
# Exercise a complete observation stop/step/re-arm without the initial '?' query.
import tempfile,struct,json
regs=[0]*33;regs[0]=0x2cf;regs[29]=0xffffff8000009000;regs[31]=0xffffff8000008800;regs[32]=0xffffff80004f9ea0
point={'label':'Backup_sync_subsystem_entry','runtime_word':'fd7bbaa9','runtime_address':hex(regs[32])}
def observe(g):
 with tempfile.TemporaryDirectory(prefix='gate102-check-',dir=Path(__file__).resolve().parent) as folder:
  journal=[]
  def qmp(cmd,args=None):journal.append(cmd);return {'return':{'status':'debug'}} if cmd=='query-status' else {'return':{}}
  o=KernelObserver(Path(folder),g,qmp,{});o.base=0xffffff80004f7000;o.points={regs[32]:point};assert o.poll();assert o.records[0]['registers']['x0']=='0x2cf';assert journal==['query-status','cont'];assert o.records[0]['step_stop']=='T05thread:2;'
seen2=run_case([('qC',['QC2']),('Hg2',['OK']),('g',[struct.pack('<33Q',*regs).hex()]),('z1,ffffff80004f9ea0,4',['OK']),('s',['T05thread:2;']),('Z1,ffffff80004f9ea0,4',['OK'])],observe)
assert '?' not in seen2 and not any(x.startswith(('M','G','P')) for x in seen2)
print('AP102_V2_RSP_QC_STOP_STEP_REARM_MODE_RESTORE_READONLY_PASS')
