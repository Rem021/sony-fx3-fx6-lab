import socket,threading
from pathlib import Path
from gate_input102 import InputGate

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
 assert g.packet('?')=='T05thread:2;'
 assert g.packet('g')=='00'*264
 assert list(g.debug_stops)==['T02thread:2;']
 assert g.packet('s')=='T05thread:2;'
 assert g.virtual_read(0xffffff8000002000,4) is None
seen=run_case([('Qqemu.PhyMemMode:0',['OK']),('mffffff8000001000,4',['fd7bbaa9']),('Qqemu.PhyMemMode:1',['OK']),('?',['T05thread:2;']),('g',['T02thread:2;','00'*264]),('s',['T05thread:2;']),('Qqemu.PhyMemMode:0',['OK']),('mffffff8000002000,4',['E01']),('Qqemu.PhyMemMode:1',['OK'])],check)
assert not any(x.startswith(('M','G','P')) for x in seen)
print('AP102_RSP_STOP_STEP_MODE_RESTORE_READONLY_PASS')
