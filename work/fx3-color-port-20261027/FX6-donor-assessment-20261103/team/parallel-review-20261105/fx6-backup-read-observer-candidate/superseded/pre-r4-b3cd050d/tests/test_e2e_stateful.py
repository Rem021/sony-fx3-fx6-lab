#!/usr/bin/env python3
"""Real HostRunner over actual QMP/RSP socketpair servers; fake guest observer only."""
import importlib.util,json,socket,tempfile,threading,time,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('h',HERE/'observer/host_runner.py');H=importlib.util.module_from_spec(spec);spec.loader.exec_module(H)
checks=[]
def check(n,f):f();checks.append(n)
class QMPState:
 def __init__(self,sock):self.sock=sock;self.state='paused';self.booted=False;self.calls=[];self.err=None
 def run(self):
  try:
   f=self.sock.makefile('rwb',buffering=0);f.write(b'{"QMP":{"version":{"qemu":{"major":1,"minor":0},"package":""},"capabilities":[]}}\n')
   while True:
    line=f.readline()
    if not line:break
    q=json.loads(line);cmd=q['execute'];self.calls.append(cmd)
    if cmd=='qmp_capabilities':resp={}
    elif cmd=='query-status':resp={'status':self.state}
    elif cmd=='cont':self.state='running';self.booted=True;resp={}
    elif cmd=='stop':self.state='paused';resp={}
    elif cmd=='quit':f.write((json.dumps({'id':q['id'],'return':{}})+'\n').encode());break
    else:resp={}
    f.write((json.dumps({'id':q['id'],'return':resp})+'\n').encode())
  except BaseException as e:self.err=repr(e)
  finally:
   try:self.sock.close()
   except:pass
class GDBState:
 def __init__(self,sock,on_continue=None):self.sock=sock;self.on_continue=on_continue;self.calls=[];self.err=None
 def run(self):
  try:
   self.sock.settimeout(2)
   while True:
    b=self.sock.recv(1)
    if not b:break
    if b!=b'$':raise ValueError('frame')
    raw=b''
    while True:
     c=self.sock.recv(1)
     if c==b'#':break
     raw+=c
    self.sock.recv(2);self.calls.append(raw.decode())
    if raw==b'c':
     self.sock.sendall(b'+')
     if self.on_continue:self.on_continue(self.sock)
     else:
      msg=b'T05thread:1;';self.sock.sendall(b'$'+msg+b'#'+f'{sum(msg)&255:02x}'.encode())
    else:self.sock.sendall(b'+$OK#'+f'{sum(b"OK")&255:02x}'.encode())
  except BaseException as e:self.err=repr(e)
  finally:
   try:self.sock.close()
   except:pass
class Q:
 def __init__(self):self.calls=[];self.states=[];self.closed=False;self.state='paused'
 def call(self,c,args=None,deadline=None):
  self.calls.append(c)
  if c=='query-status':return {'status':self.state}
  if c=='cont':self.state='running'
  if c=='stop':self.state='paused'
  return {}
 def close(self):self.closed=True
class Qemu:
 returncode=0
 def wait(self,timeout):return 0
class Locks:
 def __init__(self):self.released=False;self.acquired=False
 def acquire(self):self.acquired=True
 def release(self):self.released=True
class Obs:
 def __init__(self,*a,**k):self.done=set();self.records=[];self.possibly=set();self.entry=None
 def arm(self):pass
 def on_stop(self,s):self.done={'0x02cf0214','0x02cf0218'};self.records=[{'gdb_cpu_thread':'1','guest_tid':'unknown'}];return {'stage':'fake'}
 def cleanup(self):return {'all_removed':True,'residual':[],'results':[],'guest_resumed':False}
def e2e():
 with tempfile.TemporaryDirectory() as td:
  qa,qb=socket.socketpair();ga,gb=socket.socketpair();qs=QMPState(qb);gs=GDBState(gb)
  tq=threading.Thread(target=qs.run);tg=threading.Thread(target=gs.run);tq.start();tg.start()
  qclient=H.QMP(sock=qa);rclient=H.RSP(sock=ga)
  # QMP client owns qa; launch qmp factory would normally construct it; this test
  # injects the already-negotiated actual client, still exercising real socket I/O.
  q=Q(client=None) if False else None
  qmp_proxy=Q()
  # Wrap actual QMP to expose call/close like fake; capability already negotiated.
  qmp_proxy.call=lambda c,args=None,deadline=None:qclient.call(c,args,deadline)
  qmp_proxy.close=qclient.close
  def mapping(serial,deadline):
   assert qs.booted and qs.state=='running', 'map requested before boot cont'
   return {'pid':237,'ap':{'bias':0x7ed3ccc000}}
  d={'verify_artifacts':lambda:{},'hash_checker':lambda p: H.baseline_binding.TARGET_SHA if str(p)==str(H.baseline_binding.TARGET) else H.baseline_binding.APP_SHA,'uuid_checker':lambda:True,'run_root':str(Path(td)/'run'),'lock_factory':Locks,'launcher':lambda *a:Qemu(),'qmp_factory':lambda p:qmp_proxy,'rsp_factory':lambda p:rclient,'mapping_provider':mapping,'tls_reader':lambda:0x7f5cfff740,'callback_cancellable':True,'inherited_cleanup':lambda *a:{'passed':True,'API16_restored':True,'original_bytes_verified':True,'ack_seen':True}}
  # Replace core Observer with stateful fake for transport/lifecycle test.
  old=H.observer_core.Observer;H.observer_core.Observer=Obs
  try:
   h=H.HostRunner(d);out=h.run()
  finally:H.observer_core.Observer=old
  tq.join(2);tg.join(2)
  assert out['clean'],out
  assert qs.calls[:3]==['qmp_capabilities','query-status','cont'],qs.calls
  assert qs.booted and 'c' in gs.calls,gs.calls
  assert qs.calls.index('cont')<qs.calls.index('stop')
  assert 'qmp_quit' in [] or 'quit' in qs.calls
  assert qs.calls[-1]=='quit';assert gs.calls.count('c')==1
check('real_runner_actual_QMP_RSP_boot_order_continue_clean',e2e)
out={'status':'PASS_NO_QEMU_STATEFUL_E2E','fixture':'actual HostRunner/QMP/RSP over socketpair; fake guest observer, no QEMU','cases':checks,'count':len(checks),'runner_sha256':hashlib.sha256((HERE/'observer/host_runner.py').read_bytes()).hexdigest()}
(HERE/'tests/e2e-stateful-tests.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
