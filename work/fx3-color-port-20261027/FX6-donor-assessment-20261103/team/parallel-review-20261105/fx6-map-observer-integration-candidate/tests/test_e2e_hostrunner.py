#!/usr/bin/env python3
"""Actual frozen HostRunner/Observer/QMP/RSP four-stop, current provider/entry."""
import importlib.util,json,socket,struct,tempfile,threading,time,hashlib,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(HERE))
import live_runner as L, framed_provider as FP, run_map_observer as ENTRY
R6=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-backup-read-observer-candidate')
spec=importlib.util.spec_from_file_location('h',R6/'observer/host_runner.py');H=importlib.util.module_from_spec(spec);spec.loader.exec_module(H);core=H.observer_core
CP=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic');APP=CP/'grm-fbinit/appFw-future-skip.so';FIX=HERE/'receipts/native-target-frame.serial';M=FP.FramedProvider().select(FIX.read_text());BIAS=M['ap']['bias'];checks=[]
def check(n,f):f();checks.append(n)
def packet(s):r=s.encode();return b'$'+r+b'#'+f'{sum(r)&255:02x}'.encode()
class QMPServer:
 def __init__(self,sock):self.sock=sock;self.state='prelaunch';self.running=False;self.calls=[];self.err=None;self.caps=False
 def run(self):
  try:
   f=self.sock.makefile('rwb',buffering=0);f.write(b'{"QMP":{"version":{"qemu":{"major":1,"minor":0},"package":""},"capabilities":[]}}\n')
   while True:
    line=f.readline()
    if not line:break
    q=json.loads(line);cmd=q['execute'];self.calls.append(cmd)
    if not self.caps and cmd!='qmp_capabilities':raise RuntimeError('command before capabilities')
    if cmd=='qmp_capabilities':self.caps=True;resp={}
    elif cmd=='query-status':resp={'status':self.state,'running':self.running}
    elif cmd=='cont':self.state='running';self.running=True;resp={}
    elif cmd=='stop':self.state='paused';self.running=False;resp={}
    elif cmd=='quit':f.write((json.dumps({'id':q['id'],'return':{}})+'\n').encode());break
    else:resp={}
    f.write((json.dumps({'id':q['id'],'return':resp})+'\n').encode())
  except BaseException as e:self.err=repr(e)
  finally:
   try:self.sock.close()
   except:pass
class GDBServer:
 def __init__(self,sock):self.sock=sock;self.err=None;self.cmds=[];self.continued=0;self.state='paused';self.stop_index=0
 def _read_packet(self):
  b=self.sock.recv(1)
  if not b:return None
  while b in (b'+',b'-',b'\n',b'\r'):
   b=self.sock.recv(1)
   if not b:return None
  if b!=b'$':raise RuntimeError('bad framing '+repr(b))
  raw=b''
  while True:
   c=self.sock.recv(1)
   if c==b'#':break
   raw+=c
  tail=self.sock.recv(2)
  if int(tail,16)!=sum(raw)&255:raise RuntimeError('bad checksum')
  self.sock.sendall(b'+');return raw.decode()
 def _reply(self,body):self.sock.sendall(packet(body))
 def _send_stop(self):
  names=['entry214','return214','entry218','return218'];n=names[self.stop_index];self.stop_index+=1
  msg=b'T05thread:1;';self.sock.sendall(b'$'+msg+b'#'+f'{sum(msg)&255:02x}'.encode());self.state='stopped'
 def _regs(self):
  n=self.stop_index-1;k=core.KEYS[0] if n in (0,1) else core.KEYS[1];fp=0x7ed3d12290;buf=fp+k['slot_off'];r=[0]*33;r[29]=fp
  if n in (0,2):r[0]=buf;r[30]=BIAS+k['return_va'];r[32]=BIAS+k['thunk_va']
  else:r[0]=0xfffffc03;r[32]=BIAS+k['return_va']
  return struct.pack('<33Q',*r).hex()
 def _mem(self,addr,size):
  k=core.KEYS[0] if self.stop_index<=2 else core.KEYS[1];fp=0x7ed3d12290;buf=fp+k['slot_off']
  if addr==buf:return (b'\x01\x00\x00\x00' if self.stop_index in (1,3) else b'\x16\x16\x16\x16').hex()
  if addr in (BIAS+k['thunk_va'],BIAS+k['return_va']):return (bytes.fromhex(k['thunk_word']) if addr==BIAS+k['thunk_va'] else bytes.fromhex(k['return_word'])).hex()
  va=addr-BIAS;b=APP.read_bytes()
  for s in core.elf_loads(APP):
   if s['va']<=va and va+size<=s['va']+s['filesz']:
    off=s['fileoff']+va-s['va'];return b[off:off+size].hex()
  raise RuntimeError('unmapped m '+hex(addr))
 def _xml(self):return '<target><architecture>aarch64</architecture><feature name="org.gnu.gdb.aarch64.core"><reg name="x0" regnum="0" bitsize="64"/><reg name="x29" regnum="29" bitsize="64"/><reg name="x30" regnum="30" bitsize="64"/><reg name="sp" regnum="31" bitsize="64"/><reg name="pc" regnum="32" bitsize="64"/><reg name="SP_EL0" regnum="100" bitsize="64"/><reg name="TPIDR_EL0" regnum="101" bitsize="64"/></feature></target>'
 def run(self):
  try:
   while True:
    raw=self._read_packet()
    if raw is None:break
    self.cmds.append(raw)
    if raw.startswith('qXfer:features:read:target.xml:'):self._reply('l'+self._xml());continue
    if raw.startswith('Qqemu.PhyMemMode') or raw.startswith('qqemu.PhyMemMode'):self._reply('OK');continue
    if raw.startswith('Hg') or raw.startswith('Hc'):self._reply('OK');continue
    if raw.startswith('Z1,') or raw.startswith('z1,'):self._reply('OK');continue
    if raw=='g':self._reply(self._regs());continue
    if raw.startswith('p'):self._reply('4074ff5c7f000000' if raw=='p65' else '0000000000000000');continue
    if raw.startswith('m'):
     a,s=raw[1:].split(',');self._reply(self._mem(int(a,16),int(s,16)));continue
    if raw=='c':self.continued+=1;self.sock.sendall(b'+');self._send_stop();continue
    raise RuntimeError('unexpected GDB '+raw[:40])
  except BaseException as e:self.err=repr(e)
  finally:
   try:self.sock.close()
   except:pass
def make_deps(root):
 qa,qb=socket.socketpair();ga,gb=socket.socketpair();qs=QMPServer(qb);gs=GDBServer(gb);tq=threading.Thread(target=qs.run);tg=threading.Thread(target=gs.run);tq.start();tg.start();q=H.QMP(sock=qa);r=H.RSP(sock=ga)
 class QProxy:
  def call(self,c,args=None,deadline=None):return q.call(c,args,deadline)
  def close(self):q.close()
 def writer():
  p=Path(root)/'serial.log'
  while not p.exists():time.sleep(.01)
  raw=FIX.read_bytes();cut=40
  with p.open('wb') as f:f.write(raw[:cut]);f.flush();time.sleep(.1);f.write(raw[cut:]);f.flush()
 threading.Thread(target=writer,daemon=True).start()
 def tls():return 0x7f5cff740
 d={'verify_artifacts':lambda:{},'hash_checker':lambda p:H.baseline_binding.TARGET_SHA if str(p)==str(H.baseline_binding.TARGET) else H.baseline_binding.APP_SHA,'uuid_checker':lambda:True,'run_root':str(root),'lock_factory':lambda:type('L',(),{'acquire':lambda s:None,'release':lambda s:None})(),'launcher':lambda *a:type('P',(),{'returncode':0,'wait':lambda s,timeout:0})(),'qmp_factory':lambda p,deadline=None:QProxy(),'rsp_factory':lambda p,deadline=None:r,'mapping_provider':lambda *a:M,'tls_reader':tls,'runtime_evidence':False}
 return d,(qa,qb,ga,gb,qs,gs,tq,tg)
def test_success():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td)/'run';runner_holder={}
  def rf(r):
   deps,parts=make_deps(r);runner_holder['parts']=parts;return L.build_runner(r,deps_factory=lambda:deps)
  rc=ENTRY.main(['--approved-token',ENTRY.TOKEN,'--new-run-approval','--run-root',str(root)],rf)
  parts=runner_holder['parts'];qs=parts[4];gs=parts[5]
  rec=json.loads((root/'receipt.json').read_text())
  print('DEBUG_RECEIPT',json.dumps({k:rec.get(k) for k in ('status','error','clean','records','two_keys_observed','host_cleanup_complete','cleanup')},indent=1)[:3000])
  assert rc==0,(rc,root);assert rec['two_keys_observed'] and rec['host_cleanup_complete'] and rec['guest_restore_status']=='unknown_not_attempted';assert gs.continued==4;assert qs.calls[:3]==['qmp_capabilities','query-status','cont']
  for s in parts[:4]:
   try:s.close()
   except:pass
  for t in parts[6:]:t.join(1)
check('actual_HostRunner_Observer_QMP_RSP_four_stop_via_entry',test_success)
out={'schema':'fx6-map-observer-integration-e2e-v1','status':'PASS_OFFLINE_ACTUAL_HOSTRUNNER','tests':len(checks),'cases':checks}
(HERE/'tests/test-e2e-hostrunner.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
