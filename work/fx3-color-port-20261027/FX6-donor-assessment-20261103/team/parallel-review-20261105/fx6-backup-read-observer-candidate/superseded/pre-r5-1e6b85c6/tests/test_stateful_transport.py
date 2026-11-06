#!/usr/bin/env python3
"""Stateful socketpair tests for actual QMP and RSP classes; no QEMU."""
import importlib.util,json,socket,threading,time,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('h',HERE/'observer/host_runner.py');H=importlib.util.module_from_spec(spec);spec.loader.exec_module(H)
spec=importlib.util.spec_from_file_location('r',HERE/'observer/rsp_readonly.py');R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)
checks=[]
def check(n,f):f();checks.append(n)
def qmp_server(sock,cap_error=False):
 sock.settimeout(2);f=sock.makefile('rwb',buffering=0)
 f.write(b'{"QMP":{"version":{"qemu":{"major":1,"minor":0},"package":""},"capabilities":[]}}\n')
 line=f.readline();req=json.loads(line);assert req['execute']=='qmp_capabilities'
 if cap_error:f.write(b'{"id":"%s","error":{"class":"GenericError","desc":"caps missing"}}\n'%req['id'].encode())
 else:f.write(b'{"id":"%s","return":{}}\n'%req['id'].encode())
 while True:
  line=f.readline()
  if not line:break
  req=json.loads(line);cmd=req['execute']
  if cmd=='query-status':resp={'status':'paused'}
  elif cmd=='quit':resp={}
  else:resp={}
  f.write((json.dumps({'id':req['id'],'return':resp})+'\n').encode())
  if cmd=='quit':break
 sock.close()
def qmp_positive():
 a,b=socket.socketpair();t=threading.Thread(target=qmp_server,args=(b,));t.start()
 q=H.QMP(sock=a);assert q.call('query-status')=={'status':'paused'};q.call('quit');q.close();t.join(2);assert not t.is_alive()
check('actual_QMP_greeting_capabilities_id_match',qmp_positive)
def qmp_missing_caps():
 a,b=socket.socketpair();t=threading.Thread(target=qmp_server,args=(b,True));t.start()
 try:
  try:H.QMP(sock=a)
  except RuntimeError as e:assert 'caps missing' in str(e)
  else:raise AssertionError('missing qmp_capabilities accepted')
 finally:a.close();t.join(2)
check('actual_QMP_missing_capabilities_rejected',qmp_missing_caps)
def qmp_timeout():
 a,b=socket.socketpair()
 class D:
  total=0.15
  def remaining_total(self):return 0.15
 try:
  t0=time.monotonic()
  try:H.QMP(sock=a,deadline=D())
  except TimeoutError:pass
  else:raise AssertionError('silent QMP greeting accepted')
  assert time.monotonic()-t0<1.0
 finally:a.close();b.close()
check('actual_QMP_greeting_bounded_no_response',qmp_timeout)
def rsp_continue_immediate_stop():
 a,b=socket.socketpair();b.settimeout(2)
 def srv():
  assert b.recv(1)==b'$';raw=b''
  while True:
   c=b.recv(1)
   if c==b'#':break
   raw+=c
  assert raw==b'c';b.recv(2);b.sendall(b'+')
  msg=b'T05thread:1;';b.sendall(b'$'+msg+b'#'+f'{sum(msg)&255:02x}'.encode())
 srv_t=threading.Thread(target=srv);srv_t.start()
 r=R.RSP(a)
 try:
  assert r.send_continue(timeout=.5)=={'command':'c','ack':'+'};assert r.poll_stop(.5)=='T05thread:1;'
 finally:r.close();srv_t.join(2)
check('actual_RSP_addressless_c_immediate_T05',rsp_continue_immediate_stop)
def rsp_timeout():
 a,b=socket.socketpair();r=R.RSP(a);t0=time.monotonic()
 try:
  try:r.send_continue(timeout=.15)
  except TimeoutError:pass
  else:raise AssertionError('silent RSP continue accepted')
  assert time.monotonic()-t0<1.0
 finally:r.close();b.close()
check('actual_RSP_continue_no_response_bounded',rsp_timeout)
out={'status':'PASS_NO_QEMU_STATEFUL_TRANSPORT','fixture':'actual QMP/RSP classes over socketpair; no QEMU/guest','cases':checks,'count':len(checks),'qmp_sha256':hashlib.sha256((HERE/'observer/host_runner.py').read_bytes()).hexdigest(),'rsp_sha256':hashlib.sha256((HERE/'observer/rsp_readonly.py').read_bytes()).hexdigest()}
(HERE/'tests/stateful-transport-tests.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
