"""Local Unix GDB gate: the sole write is 8 bytes in new software-owned RAM."""
from pathlib import Path
import socket,os,struct,time,json
PHYS=0x41df00000;MAGIC=0x3545594b334d5253;BASE_KEYS={3,0x30,0x15,0x1af,0x1ac,0x1ab}
def valid_command(step,key,hold_ms,count,delete_key=0,max_steps=4096):
 return 32<=max_steps<=4096 and count<max_steps and step==count+1 and 1<=step<=max_steps and key in BASE_KEYS|({delete_key} if delete_key else set()) and 50<=hold_ms<=200
class InputGate:
 def __init__(self,run,delete_key=0,max_steps=4096,socket_path=None):self.run=Path(run);self.sock=None;self.history=[];self.delete_key=delete_key;self.max_steps=max_steps;self.socket_path=socket_path
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
  if not self.socket_path:raise RuntimeError('short GDB socket path required; no global chdir fallback')
  self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.settimeout(3)
  self.sock.connect(self.socket_path)
  if self.packet('Qqemu.PhyMemMode:1')!='OK':raise RuntimeError('physical GDB mode unavailable')
  if self.packet('qqemu.PhyMemMode')!='1':raise RuntimeError('physical GDB mode readback failed')
 def command(self,step,key,hold_ms,observed_page,reason):
  if not observed_page or not reason or not valid_command(step,key,hold_ms,len(self.history),self.delete_key,self.max_steps):raise ValueError('Unapproved host-step command/key/hold/visual reasoning')
  self.connect();raw=bytes.fromhex(self.packet(f'm{PHYS:x},40'))
  if len(raw)!=64:raise RuntimeError('short host-step software header')
  magic,previous,oldkey,oldhold,reserved,done,donekey=struct.unpack_from('<Q6I',raw)
  result=struct.unpack_from('<I',raw,52)[0]
  if magic!=MAGIC or previous!=step-1 or done!=step-1 or reserved or result:raise RuntimeError('host-step software identity/order/result mismatch')
  data=struct.pack('<III',step,key,hold_ms);address=PHYS+8
  if self.packet(f'M{address:x},c:{data.hex()}')!='OK':raise RuntimeError('host-step command write failed')
  check=bytes.fromhex(self.packet(f'm{address:x},c'))
  if check!=data:raise RuntimeError('host-step command readback mismatch')
  item={'step':step,'key':hex(key),'hold_ms':hold_ms,'observed_page':observed_page,'reason':reason,'physical':hex(address),'bytes':12,'before_header_hex':raw.hex(),'written_hex':data.hex(),'readback_hex':check.hex(),'software_gate_only':True,'no_original_UI_or_parameter_write':True,'host_monotonic':time.monotonic()};self.history.append(item);(self.run/'ap101-host-input-gate.json').write_text(json.dumps(self.history,ensure_ascii=False,indent=2)+'\n');return item

 def shutdown_control(self):
  self.connect();address=0x41d400030;magic=bytes.fromhex(self.packet('m41d400000,8'))
  if magic!=b'F100FILE':raise RuntimeError('new observer reservation identity mismatch')
  data=struct.pack('<Q',0x100c1ea9)
  if self.packet(f'M{address:x},8:{data.hex()}')!='OK' or bytes.fromhex(self.packet(f'm{address:x},8'))!=data:raise RuntimeError('shutdown observer control readback failed')
  (self.run/'ap101-shutdown-control.json').write_text(json.dumps({'physical':hex(address),'bytes':8,'written_hex':data.hex(),'readback_verified':True,'software_observer_only':True,'reason':'after observation and final snapshots, stop owned guest AP then restore native deviceAPI; keep main module resident'},indent=2)+'\n')
