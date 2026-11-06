from gate_input93 import InputGate,PHYS,MAGIC,KEYS
from pathlib import Path
import struct,json
R=Path(__file__).resolve().parent;D=R/'ap93-host-gate-fixture';D.mkdir(exist_ok=True)
class Mock:
 def __init__(self):self.buf=b'';self.requests=[];self.header=bytearray(48);struct.pack_into('<Q',self.header,0,MAGIC)
 def sendall(self,p):
  if p==b'+':return
  a=p[1:p.index(b'#')].decode();self.requests.append(a)
  if a.startswith('m'):
   addr,n=a[1:].split(',');offset=int(addr,16)-PHYS;value=self.header[offset:offset+int(n,16)].hex()
  elif a.startswith('M'):
   loc,h=a[1:].split(':');addr,n=loc.split(',');assert int(addr,16)==PHYS+8 and int(n,16)==8;self.header[8:16]=bytes.fromhex(h);value='OK'
  else:raise AssertionError(a)
  b=value.encode();self.buf+=b'+$'+b+b'#'+f'{sum(b)%256:02x}'.encode()
 def recv(self,n):v=self.buf[:1];self.buf=self.buf[1:];return v
m=Mock();g=InputGate(D);g.sock=m
for i,k in enumerate(KEYS,1):
 if i>1:struct.pack_into('<I',m.header,16,i-1)
 g.command(i,k)
for step,key in [(0,0x1ab),(6,0x1ac),(1,0x30)]:
 try:g.command(step,key);raise AssertionError('invalid key accepted')
 except ValueError:pass
writes=[x for x in m.requests if x.startswith('M')];assert len(writes)==5 and all(x.startswith(f'M{PHYS+8:x},8:') for x in writes);assert len(g.history)==5
(R/'ap93-gate-host-check.json').write_text(json.dumps({'mock_split_checksum_reads':True,'approved_sequences':5,'invalid_sequences_rejected':3,'all_writes_same_new_reserved_8bytes':True,'physical':hex(PHYS+8),'write_sizes':[8]*5,'QMP_GDB_native_runtime':'not yet tested'},indent=2)+'\n');print('GATE PASS 5 approved/3 rejected/exact reserved8B/fragmented stream')
