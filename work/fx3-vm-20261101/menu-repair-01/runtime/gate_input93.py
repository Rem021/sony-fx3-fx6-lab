"""Local Unix GDB gate: the sole write is 8 bytes in new software-owned RAM."""
from pathlib import Path
import socket,os,struct,time,json
PHYS=0x41df00000;MAGIC=0x3345594b334d5253;KEYS=[0x1ab,0x30,0x30,0x1af,0x1ac]
class InputGate:
 def __init__(self,run):self.run=Path(run);self.sock=None;self.history=[]
 def exact(self,n):
  out=bytearray()
  while len(out)<n:
   chunk=self.sock.recv(n-len(out))
   if not chunk:raise RuntimeError('GDB gate stream ended')
   out.extend(chunk)
  return bytes(out)
 def packet(self,payload):
  data=payload.encode();self.sock.sendall(b'$'+data+b'#'+f'{sum(data)%256:02x}'.encode())
  while True:
   c=self.sock.recv(1)
   if not c:raise RuntimeError('GDB gate stream ended')
   if c in (b'+',b'-'):continue
   if c!=b'$':continue
   out=bytearray()
   while True:
    c=self.sock.recv(1)
    if c==b'#':break
    if not c:raise RuntimeError('GDB gate packet ended')
    out.extend(c)
   checksum=self.exact(2)
   if len(checksum)!=2 or int(checksum,16)!=sum(out)%256:raise RuntimeError('GDB packet checksum mismatch')
   self.sock.sendall(b'+');v=out.decode()
   if v.startswith(('T','S','O')) and v!='OK' and (v.startswith(('T','S')) or v.startswith('O') and v!='OK'):continue
   return v
 def connect(self):
  if self.sock:return
  self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.settimeout(3);old=Path.cwd()
  try:os.chdir(self.run);self.sock.connect('g')
  finally:os.chdir(old)
  if self.packet('Qqemu.PhyMemMode:1')!='OK':raise RuntimeError('physical GDB mode unavailable')
  if self.packet('qqemu.PhyMemMode')!='1':raise RuntimeError('physical GDB mode readback failed')
 def command(self,step,key):
  if not 1<=step<=5 or key!=KEYS[step-1]:raise ValueError('Unapproved synthetic command')
  self.connect();raw=bytes.fromhex(self.packet(f'm{PHYS:x},30'))
  if len(raw)!=48:raise RuntimeError('short software gate read')
  magic,previous,oldkey,done=struct.unpack_from('<QIII',raw)
  if magic!=MAGIC or previous!=step-1 or done!=step-1:raise RuntimeError('software gate identity/order mismatch')
  data=struct.pack('<II',step,key);address=PHYS+8
  if self.packet(f'M{address:x},8:{data.hex()}')!='OK':raise RuntimeError('software command write failed')
  check=bytes.fromhex(self.packet(f'm{address:x},8'))
  if check!=data:raise RuntimeError('software command readback mismatch')
  item={'step':step,'key':hex(key),'physical':hex(address),'bytes':8,'before_header_hex':raw.hex(),'written_hex':data.hex(),'readback_hex':check.hex(),'software_gate_only':True,'no_original_UI_or_parameter_write':True,'host_monotonic':time.monotonic()};self.history.append(item);(self.run/'ap93-host-input-gate.json').write_text(json.dumps(self.history,indent=2)+'\n');return item
