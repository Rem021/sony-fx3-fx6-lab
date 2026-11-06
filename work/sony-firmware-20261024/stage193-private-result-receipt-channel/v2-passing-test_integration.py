"""Real unprivileged peers + same-process SDK-shaped fake owner integration.

Refuses the native artifact. Never launches sudo/Terminal/IOKit/camera code.
All files are new project-local fixtures; cleanup only our live socket nodes.
"""
from pathlib import Path
from hashlib import sha256
import array, contextlib, ctypes as C, errno, importlib.util, json, mmap, os, plistlib, secrets, socket, struct, subprocess, sys, time, traceback
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOCKET_ROOT=ROOT/'work/ipc193'
BUILD=json.loads((HERE/'build-receipt-v2.json').read_text())
HELPER=Path(BUILD['builds']['fixture']['path'])
assert HELPER.name=='owner-fixture-helper' and sha256(HELPER.read_bytes()).hexdigest()==BUILD['builds']['fixture']['sha256']
assert 'IOKit.framework' not in BUILD['builds']['fixture']['dependencies']
assert not BUILD['native_build_released'] and not BUILD['native_helper_executed']
assert os.getuid()==os.geteuid()!=0
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
for m in BUILD['sources']:assert sha256((HERE/m['path']).read_bytes()).hexdigest()==m['sha256']
sys.path.insert(0,str(HERE))
import receipt_receiver as R
LIB=C.CDLL(BUILD['builds']['ipc']['path'],use_errno=True)
def function(name,result,args):
 f=getattr(LIB,name);f.restype=result;f.argtypes=args;return f
init=function('fx3_entry_init',C.c_int,[C.c_void_p,C.c_size_t,C.c_uint32,C.c_uint32,C.c_void_p,C.c_void_p,C.c_void_p])
fields=function('fx3_entry_fixture_fields',C.c_int,[C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint64,C.c_uint64])
pid_info=function('fx3_entry_pid_info',C.c_int,[C.c_uint32,C.POINTER(C.c_uint32),C.POINTER(C.c_uint64),C.POINTER(C.c_uint64)])
pid_path=function('fx3_entry_pid_path',C.c_int,[C.c_uint32,C.c_void_p,C.c_uint32])
layout=function('fx3_entry_layout',C.c_uint32,[C.c_uint32])
ipc_layout=function('fx3_ipc_layout',C.c_uint32,[C.c_uint32])
ready=function('fx3_entry_ready',C.c_uint32,[C.c_void_p]);ack=function('fx3_entry_ack',None,[C.c_void_p])
completed=function('fx3_entry_completed',C.c_uint32,[C.c_void_p]);value=function('fx3_entry_value',C.c_uint64,[C.c_void_p,C.c_uint32])
gate=function('fx3_entry_fixture_gate',None,[C.c_void_p,C.c_uint32]);stop=function('fx3_ipc_stop',None,[C.c_void_p])
def probe(pid):
 uid=C.c_uint32();sec=C.c_uint64();usec=C.c_uint64();C.set_errno(0)
 if pid_info(pid,C.byref(uid),C.byref(sec),C.byref(usec)):
  if C.get_errno()==errno.ESRCH:return None
  raise OSError(C.get_errno(),'local helper PID metadata')
 path=C.create_string_buffer(4096)
 if pid_path(pid,path,4096):raise OSError('local helper executable metadata unavailable')
 actual=os.fsdecode(path.value)
 return R.Identity(uid.value,pid,sec.value,usec.value,actual,sha256(Path(actual).read_bytes()).hexdigest())

class Grant(C.Structure):
 _fields_=[('schema',C.c_uint32),('mode',C.c_uint32),('uid',C.c_uint32),('scope',C.c_uint32),
 ('nonce',C.c_ubyte*16),('key',C.c_ubyte*32),('tag',C.c_ubyte*32),
 ('claimed',C.c_uint32),('started',C.c_uint32),('completed',C.c_uint32),('pid',C.c_uint32),
 ('sec',C.c_uint64),('usec',C.c_uint64),('started_ns',C.c_uint64),('work_deadline',C.c_uint64),('final_deadline',C.c_uint64),
 ('result',C.c_int32),('fail',C.c_uint32),('option',C.c_uint32),('block',C.c_uint32),
 ('observed',C.c_ubyte*32),('digest',C.c_ubyte*32),('observer',C.c_uint32),('observer_sec',C.c_uint64),('observer_usec',C.c_uint64),
 ('ready',C.c_uint32),('ack',C.c_uint32)]
assert C.sizeof(Grant)==layout(2)
def wait(predicate,timeout=4):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  if predicate():return
  time.sleep(.005)
 raise AssertionError('specific local fixture state wait timed out')

class Job:
 serial=0
 def __init__(self,option=0,block=0,fail=0,observed=b'A'*32,capture_files=False,guard_path=None,peer_ack='normal'):
  Job.serial+=1;self.name=f'{Job.serial:03d}-{secrets.token_hex(3)}'
  self.path=HERE/'runs'/self.name;self.path.mkdir(mode=0o700)
  SOCKET_ROOT.mkdir(mode=0o700,exist_ok=True);self.sockdir=SOCKET_ROOT/self.name;self.sockdir.mkdir(mode=0o700)
  self.sockpath=self.sockdir/'s';assert len(os.fsencode(self.sockpath))<104
  self.server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.server.bind(str(self.sockpath));os.chmod(self.sockpath,0o600);self.server.listen(1);self.server.settimeout(4)
  self.conn=None;self.proc=None;self.record=None;self.frame_fd=None;self.held=False;self.expected_wire=None;self.expected_pipes=None;self.forced_fixture_exit=False
  self.receipt=None;self.receiver=None;self.receipt_failure=None
  fd=os.open(self.path/'shared.bin',os.O_RDWR|os.O_CREAT|os.O_EXCL,0o600);os.fchmod(fd,0o600);os.ftruncate(fd,4096)
  self.mm=mmap.mmap(fd,4096);os.close(fd);self.buf=(C.c_ubyte*4096).from_buffer(self.mm);self.ptr=C.addressof(self.buf)
  self.grant=Grant.from_buffer(self.mm,layout(1));self.nonce=secrets.token_bytes(16);self.id=0
  assert init(self.ptr,4096,1,os.getuid(),self.nonce,b'K'*32,b'A'*32)==0
  uid=C.c_uint32();sec=C.c_uint64();usec=C.c_uint64();assert pid_info(os.getpid(),C.byref(uid),C.byref(sec),C.byref(usec))==0
  assert uid.value==os.getuid()
  assert fields(self.ptr,fail,option,block,observed,os.getpid(),sec.value,usec.value)==0
  self.guard_path=Path(guard_path) if guard_path else self.path/'global.journal'
  self.argv=[str(HELPER),str(self.path/'shared.bin'),self.nonce.hex(),str(self.path/'entry.once'),str(self.sockpath),str(self.guard_path)]
  if capture_files:
   self.orphan_stdout=(self.path/'orphan-stdout.txt').open('wb');self.orphan_stderr=(self.path/'orphan-stderr.txt').open('wb')
   self.proc=subprocess.Popen(self.argv,stdout=self.orphan_stdout,stderr=self.orphan_stderr)
  else:self.proc=subprocess.Popen(self.argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  wait(lambda: ready(self.ptr) or self.proc.poll() is not None)
  assert ready(self.ptr),self.proc.communicate()
  assert self.grant.pid==self.proc.pid
  self.verified=R.capture_helper(self.proc.pid,os.getuid(),str(HELPER),BUILD['builds']['fixture']['sha256'],probe,mode='fixture')
  assert (self.grant.sec,self.grant.usec)==(self.verified.identity.sec,self.verified.identity.usec)
  ack(self.ptr)
  self.conn,_=self.server.accept();self.conn.settimeout(4)
  if option&(1048576|2097152):
   # Root-side peer check deliberately fails before the socket ACK barrier.
   # These negative cases have no accepted authenticated result channel.
   try:self.receiver=R.Receiver(self.conn,self.verified,self.nonce)
   except OSError:pass
  else:
   self.receiver=R.Receiver(self.conn,self.verified,self.nonce)
   if peer_ack=='normal':self.receiver.acknowledge()
   elif peer_ack=='wrong_nonce':self.conn.sendall(b'FX3ACK01'+b'Z'*16)
   elif peer_ack=='none':pass
   elif peer_ack in ('rights32','rights200'):
    fd=os.open('/dev/null',os.O_RDONLY)
    try:self.conn.sendmsg([b'FX3ACK01'+self.nonce],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[fd]*(32 if peer_ack=='rights32' else 200)))])
    finally:os.close(fd)
   else:raise ValueError('unknown own ACK fixture')
 def packet(self,op,payload=b'',**kw):
  self.id+=1;deadline=min(time.monotonic_ns()+500_000_000,self.grant.work_deadline)
  return struct.pack('<IIQQQII16s',0x31385146,1,kw.get('id',self.id),kw.get('generation',17),kw.get('deadline',deadline),op,len(payload),kw.get('nonce',self.nonce))+payload.ljust(516,b'\0')
 def read_exact(self,n):
  data=b''
  while len(data)<n:
   chunk=self.conn.recv(n-len(data))
   if not chunk:raise EOFError('own fixture stream ended')
   data+=chunk
  return data
 def response(self):
  n=struct.unpack('<I',self.read_exact(4))[0];assert n==676
  data=self.read_exact(n);assert struct.unpack_from('<II',data)==(0x52385146,1) and data[48:64]==self.nonce
  assert struct.unpack_from('<I',data,40)[0]==0 # never body completion proof
  return struct.unpack_from('<I',data,16)[0],data
 def send(self,op,payload=b'',fragment=False,**kw):
  data=self.packet(op,payload,**kw);frame=struct.pack('<I',len(data))+data
  if fragment:
   for chunk in (frame[:1],frame[1:3],frame[3:57],frame[57:]):self.conn.sendall(chunk);time.sleep(.005)
  else:self.conn.sendall(frame)
  return self.response()
 def finish(self,expected=0):
  wait(lambda:completed(self.ptr) or self.proc.poll() is not None)
  out,err=self.proc.communicate(timeout=4)
  (self.path/'stdout.txt').write_bytes(out);(self.path/'stderr.txt').write_bytes(err)
  assert self.proc.returncode==0,(self.proc.returncode,out,err)
  assert b'ERROR: AddressSanitizer' not in err and b'runtime error:' not in err,err
  self.record=json.loads(out);assert self.record['native_return'] in (expected if isinstance(expected,tuple) else (expected,)),self.record
  assert self.record['fd_count_before']==self.record['fd_count_after'],self.record
  assert not self.record['physical_camera_acceptance']
  result=bytes(self.mm[ipc_layout(1):ipc_layout(1)+layout(4)])
  assert sha256(result).hexdigest()==self.record['result_sha256'],self.record
  self.receive_receipt(required=self.record['receipt_delivered'])
  if self.receipt:
   assert self.receipt['phase']=='COMPLETE' and self.receipt['native_return']==self.record['native_return']
   assert self.receipt['result_sha256']==self.record['result_sha256']
   assert R.observe_completion(self.receipt,self.verified,probe)['helper_terminal_observed']
  return self.record
 def receive_receipt(self,required=True):
  if self.receipt is not None:return self.receipt
  try:
   if self.receiver is None:raise R.Rejected('peer handshake never verified')
   raw,self.receipt=self.receiver.receive(time.monotonic()+1)
   (self.path/'private-receipt.bin').write_bytes(raw)
   (self.path/'private-receipt.json').write_text(json.dumps({k:v for k,v in self.receipt.items() if k!='result_bytes'},indent=2)+'\n')
  except (R.Rejected,EOFError,TimeoutError,OSError) as e:
   self.receipt_failure=repr(e)
   (self.path/'private-receipt-unavailable.json').write_text(json.dumps({'error':repr(e),'status':'UNKNOWN','automatic_retry':False})+'\n')
   if required:raise
  return self.receipt
 def retain(self):
  wait(lambda:value(self.ptr,2)==1)
  self.held=True;assert not completed(self.ptr) and self.proc.poll() is None
  assert value(self.ptr,3)==3 and value(self.ptr,5)==1
  if self.conn:
   self.receive_receipt();assert self.receipt['phase']=='HELD'
   assert R.observe_completion(self.receipt,self.verified,probe)['status']=='OWNER_RETAINED'
  return self
 def detach(self):
  self.frame_fd=os.open(self.path/'shared.bin',os.O_RDWR)
  del self.grant;del self.buf;self.mm.close();self.mm=None;self.ptr=None
 def fake_gate(self,n):
  if self.ptr is not None:gate(self.ptr,n)
  else:os.pwrite(self.frame_fd,struct.pack('<I',n),ipc_layout(2))
 def close(self):
  if self.conn:self.conn.close();self.conn=None
  self.server.close()
  if self.proc and self.proc.poll() is None:
   self.fake_gate(1);time.sleep(.08);self.fake_gate(2)
   try:out,err=self.proc.communicate(timeout=4)
   except subprocess.TimeoutExpired:
    self.forced_fixture_exit=True;self.proc.kill();out,err=self.proc.communicate(timeout=4)
   (self.path/'cleanup-stdout.txt').write_bytes(out);(self.path/'cleanup-stderr.txt').write_bytes(err)
   if self.held:
    assert self.proc.returncode==90 and json.loads(out)['cleanup_calls']==[0,0,0],(out,err,self.proc.returncode)
    if self.expected_wire is not None:assert json.loads(out)['wire_calls']==self.expected_wire,(out,self.expected_wire)
    if self.expected_pipes is not None:assert json.loads(out)['last_pipes']==self.expected_pipes,(out,self.expected_pipes)
   assert not self.forced_fixture_exit,'own fixture cleanup unexpectedly required kill'
   assert b'ERROR: AddressSanitizer' not in err and b'runtime error:' not in err,err
  if self.sockpath.exists():self.sockpath.unlink()
  self.sockdir.rmdir()
  if self.ptr is not None:del self.grant;del self.buf;self.mm.close()
  if self.frame_fd is not None:os.close(self.frame_fd)
 def __enter__(self):return self
 def __exit__(self,*args):self.close()

results=[]
def case(name,fn):
 before=Job.serial;start=time.monotonic()
 try:fn();results.append({'name':name,'status':'PASS','processes':Job.serial-before,'seconds':time.monotonic()-start})
 except BaseException as exc:
  results.append({'name':name,'status':'FAIL','error':repr(exc),'traceback':traceback.format_exc()})
  with (HERE/('integration-failure-'+str(time.time_ns())+'.json')).open('x') as out:json.dump({'results':results},out,indent=2)
  raise
def clean(fragment=False,option=0):
 with Job(option=option) as j:
  assert j.send(1,fragment=fragment)[0]==0;assert j.send(5)[0]==0;r=j.finish()
  assert r['wire_calls']==[0,0,0]
  assert r['fixture_calls'][8:11]==([1,0,1] if option&128 else [1,1,1])
def denied_frame(**kw):
 with Job() as j:
  assert j.send(1,**kw)[0]==1;r=j.finish(1);assert r['wire_calls']==[0,0,0]
def malformed_prefix(n):
 with Job() as j:
  j.conn.sendall(struct.pack('<I',n));r=j.finish(1);assert r['wire_calls']==[0,0,0]
def rights(count):
 with Job() as j:
  fd=os.open('/dev/null',os.O_RDONLY)
  try:j.conn.sendmsg([struct.pack('<I',572)],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[fd]*count))])
  finally:os.close(fd)
  r=j.finish(1);assert r['wire_calls']==[0,0,0]
def peer_mismatch(option):
 with Job(option=option) as j:
  r=j.finish(3);assert r['fixture_calls']==[0]*12 and r['wire_calls']==[0,0,0]
START=bytes.fromhex('4301ff37aad70000');STOP=bytes.fromhex('430100c855280000')
def auth_packet(command):return struct.pack('>HH',(~command)&65535,0)+(b'\x01'+bytes(511) if command==3 else bytes(512))
def authentication(option=4096,stop_after=True):
 with Job(option=option) as j:
  assert j.send(1)[0]==0;assert j.send(2,START)[0]==0;assert j.send(1)[0]==0
  for cmd in (1,3,1,3,1,3,5):assert j.send(3,auth_packet(cmd))[0]==0
  if stop_after:assert j.send(4,STOP)[0]==0
  assert j.send(5)[0]==4;j.expected_wire=[2 if stop_after else 1,7,7];j.expected_pipes=[1,2] if option&8192 else [2,1];j.retain()
def reject_start():
 with Job() as j:
  j.conn.sendall(struct.pack('<I',572)+j.packet(2,START));r=j.finish(1);assert r['wire_calls']==[0,0,0]
def blocked(op):
 with Job(option=4096,block=0x10000|(op<<8)|12) as j:
  assert j.send(1)[0]==0
  if op!=1:assert j.send(2,START)[0]==0;assert j.send(1)[0]==0
  packet=j.packet(2,START) if op==1 else j.packet(3,auth_packet(1))
  j.conn.sendall(struct.pack('<I',572)+packet)
  wait(lambda:value(j.ptr,8)==op and value(j.ptr,4)==op)
  assert value(j.ptr,4)==op and not completed(j.ptr) and j.proc.poll() is None
  stop(j.ptr);time.sleep(.07)
  assert j.proc.poll() is None and not completed(j.ptr)
  j.conn.close();j.conn=None;gate(j.ptr,1);j.expected_wire={1:[1,0,0],2:[1,1,0],3:[1,1,1]}[op];j.retain()
def report_tamper():
 with Job() as j:
  assert j.send(1)[0]==0
  C.memset(j.ptr+ipc_layout(1),0xff,layout(4))
  j.grant.result=0x12345678;j.grant.pid=1
  assert j.send(5)[0]==0;r=j.finish();assert r['pid']==j.proc.pid
def deadline_tamper():
 with Job() as j:
  assert j.send(1)[0]==0;j.grant.work_deadline=(1<<64)-1;j.grant.final_deadline=(1<<64)-1
  start=time.monotonic();j.finish(1);assert time.monotonic()-start<3
def held_tamper():
 with Job(option=4096) as j:
  assert j.send(1)[0]==0;assert j.send(2,START)[0]==0;assert j.send(5)[0]==4;j.retain()
  C.memset(j.ptr+ipc_layout(1),0,layout(4));time.sleep(.08)
  assert j.proc.poll() is None and not completed(j.ptr);wait(lambda:value(j.ptr,2)==1)
def replay():
 with Job() as j:
  assert j.send(5)[0]==0;j.finish()
  r=subprocess.run(j.argv,capture_output=True,timeout=3);assert r.returncode==67 and b'fixed_grant_consumed' in r.stderr
def idle_stop():
 with Job() as j:
  assert j.send(1)[0]==0;start=time.monotonic();stop(j.ptr);j.finish(1);assert time.monotonic()-start<1
def max_requests():
 with Job() as j:
  for _ in range(64):assert j.send(6)[0]==0
  r=j.finish();assert r['wire_calls']==[0,0,0]
def observer_death():
 # Kill ONLY the own unprivileged observer; the fake native owner remains live.
 child_code='''import importlib.util,json,sys,time
from pathlib import Path
spec=importlib.util.spec_from_file_location('own_fixture_integration',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
j=m.Job(option=4096,block=0x10000|(2<<8)|12,capture_files=True)
assert j.send(1)[0]==0;assert j.send(2,m.START)[0]==0;assert j.send(1)[0]==0
p=j.packet(3,m.auth_packet(1));j.conn.sendall(m.struct.pack('<I',572)+p)
m.wait(lambda:m.value(j.ptr,8)==2 and m.value(j.ptr,4)==2)
print(json.dumps({'path':str(j.path),'pid':j.proc.pid,'socket':str(j.sockpath),'mode':'own-fixture'}),flush=True)
while True:time.sleep(.05)
'''
 observer=subprocess.Popen([sys.executable,'-B','-c',child_code,str(Path(__file__).resolve())],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 line=observer.stdout.readline();assert line,(observer.poll(),observer.stderr.read())
 info=json.loads(line);assert info['mode']=='own-fixture'
 path=Path(info['path']);assert path.parent==HERE/'runs'
 fd=os.open(path/'shared.bin',os.O_RDWR);mm=mmap.mmap(fd,4096);os.close(fd)
 buf=(C.c_ubyte*4096).from_buffer(mm);ptr=C.addressof(buf)
 uid=C.c_uint32();sec=C.c_uint64();usec=C.c_uint64()
 try:
  observer.kill();observer.wait(timeout=3) # not the owner or an active provider
  time.sleep(.08)
  assert pid_info(info['pid'],C.byref(uid),C.byref(sec),C.byref(usec))==0
  assert value(ptr,4)==2 and not completed(ptr)
  gate(ptr,1) # explicit release of a fake syscall only
  wait(lambda:value(ptr,2)==1)
  assert not completed(ptr) and value(ptr,3)==3
  gate(ptr,2) # local fixture exit, no cleanup/recovery receipt
  wait(lambda:pid_info(info['pid'],C.byref(uid),C.byref(sec),C.byref(usec))!=0)
  out=(path/'orphan-stdout.txt').read_text();err=(path/'orphan-stderr.txt').read_text()
  d=json.loads(out);assert d['cleanup_calls']==[0,0,0] and d['wire_calls']==[1,1,0]
  assert 'ERROR: AddressSanitizer' not in err and 'runtime error:' not in err
 finally:
  gate(ptr,1);time.sleep(.03);gate(ptr,2)
  del buf;mm.close();observer.stdout.close();observer.stderr.close()
 sock=Path(info['socket']);assert sock.parent.parent==SOCKET_ROOT
 if sock.exists():sock.unlink()
 sock.parent.rmdir()
def zero_data_rights():
 with Job() as j:
  fd=os.open('/dev/null',os.O_RDONLY)
  try:j.conn.sendmsg([b''],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[fd]*32))])
  finally:os.close(fd)
  j.conn.shutdown(socket.SHUT_WR);r=j.finish((1,3));assert r['wire_calls']==[0,0,0]
def journal_states(path):
 raw=path.read_bytes();assert len(raw)%256==0
 states=[];previous=bytes(32)
 for at in range(0,len(raw),256):
  r=raw[at:at+256];assert sha256(r[:224]).digest()==r[224:] and r[104:136]==previous
  previous=r[224:];states.append(struct.unpack_from('<I',r,20)[0])
 return states
def competing_instances():
 with Job(block=7) as a:
  wait(lambda:value(a.ptr,8)==7 and value(a.ptr,6)==7)
  with Job(guard_path=a.guard_path) as b:
   r=b.finish(3);assert r['global_guard_result']==1 and r['fixture_calls']==[0]*12
  assert journal_states(a.guard_path)==[1]
  a.fake_gate(1);assert a.send(5)[0]==0;a.finish()
  with Job(guard_path=a.guard_path) as c:
   assert c.send(5)[0]==0;c.finish()
  assert journal_states(a.guard_path)==[1,2,1,2]
def retained_blocks_new_grant():
 path=None
 with Job(option=4096) as a:
  path=a.guard_path;assert a.send(1)[0]==0;assert a.send(2,START)[0]==0;assert a.send(5)[0]==4;a.retain()
  with Job(guard_path=path) as b:
   r=b.finish(3);assert r['global_guard_result']==1 and r['fixture_calls']==[0]*12
 assert journal_states(path)==[1]
 with Job(guard_path=path) as c:
  r=c.finish(3);assert r['global_guard_result']==3 and r['fixture_calls']==[0]*12
def uncertain_cleanup_blocks_new_grant():
 with Job(fail=10) as a:
  assert a.send(5)[0]==0;a.finish(2);path=a.guard_path
 assert journal_states(path)==[1,3]
 with Job(guard_path=path) as b:
  r=b.finish(3);assert r['global_guard_result']==3 and r['fixture_calls']==[0]*12
def frame_fault_idle(hardlink=False):
 with Job() as j:
  assert j.send(1)[0]==0
  j.detach()
  if hardlink:os.link(j.path/'shared.bin',j.path/'second-hardlink.bin')
  else:
   (j.path/'pre-truncate-synthetic-frame.bin').write_bytes(os.pread(j.frame_fd,4096,0));os.ftruncate(j.frame_fd,0)
  out,err=j.proc.communicate(timeout=4)
  (j.path/'frame-fault-stdout.txt').write_bytes(out);(j.path/'frame-fault-stderr.txt').write_bytes(err)
  assert j.proc.returncode==0 and b'ERROR: AddressSanitizer' not in err and b'runtime error:' not in err
  d=json.loads(out);assert d['native_return']==1 and d['frame_io_failed'] and d['fixture_calls'][8:11]==[1,1,1]
  assert d['wire_calls']==[0,0,0] and d['fd_count_before']==d['fd_count_after']
  j.receive_receipt();assert j.receipt['frame_io_failed']
  assert R.observe_completion(j.receipt,j.verified,probe)['status']=='HOST_ABORT_RETURN_OBSERVED'
  assert journal_states(j.guard_path)==[1,2]
def frame_truncate_while_call_pending():
 with Job(option=4096,block=0x10000|(1<<8)|12) as j:
  assert j.send(1)[0]==0
  p=j.packet(2,START);j.conn.sendall(struct.pack('<I',572)+p)
  wait(lambda:value(j.ptr,8)==1 and value(j.ptr,4)==1)
  j.detach();(j.path/'pre-truncate-synthetic-frame.bin').write_bytes(os.pread(j.frame_fd,4096,0));os.ftruncate(j.frame_fd,0)
  time.sleep(.07);assert j.proc.poll() is None
  with Job(guard_path=j.guard_path) as b:
   r=b.finish(3);assert r['global_guard_result']==1 and r['fixture_calls']==[0]*12
  j.conn.close();j.conn=None;j.fake_gate(1);time.sleep(.08)
  assert j.proc.poll() is None and journal_states(j.guard_path)==[1]
  j.held=True;j.expected_wire=[1,0,0]

def run_all():
 case('observe_end_real_peer',clean)
 case('fragmented_stream',lambda:clean(fragment=True))
 case('reversed_pipe_map',lambda:clean(option=8192))
 case('without_storage_driver',lambda:clean(option=128))
 case('nonce_mismatch',lambda:denied_frame(nonce=b'Z'*16))
 case('generation_mismatch',lambda:denied_frame(generation=18))
 case('zero_id',lambda:denied_frame(id=0))
 case('expired_deadline',lambda:denied_frame(deadline=1))
 for n in (0,571,573,0xffffffff):case(f'bad_stream_size_{n}',lambda n=n:malformed_prefix(n))
 case('SCM_RIGHTS_rejected_closed',lambda:rights(1))
 case('large_SCM_RIGHTS_rejected_closed',lambda:rights(32))
 case('max_accepted_test_SCM_RIGHTS_closed',lambda:rights(200))
 case('wrong_kernel_peer_pid_before_owner',lambda:peer_mismatch(1048576))
 case('wrong_peer_birth_before_owner',lambda:peer_mismatch(2097152))
 case('native_scope_denies_START',reject_start)
 case('fake_auth_STOP_not_body_exit',authentication)
 case('fake_auth_reversed_endpoints',lambda:authentication(option=4096|8192))
 case('fake_auth_without_STOP_retains',lambda:authentication(stop_after=False))
 for op in (1,2,3):case(f'blocked_native_op_{op}_no_cleanup',lambda op=op:blocked(op))
 case('public_result_not_owner_state',report_tamper)
 case('public_deadline_not_private_budget',deadline_tamper)
 case('public_result_cannot_release_retained_owner',held_tamper)
 case('single_use_lease_replay_denied',replay)
 case('cooperative_idle_stop',idle_stop)
 case('request_limit_64',max_requests)
 case('real_observer_death_while_fake_OUT_pending',observer_death)
 case('zero_data_rights_no_descriptor_leak',zero_data_rights)
 case('competing_instances_denied_before_owner',competing_instances)
 case('retained_and_dead_grant_still_block_next',retained_blocks_new_grant)
 case('unknown_cleanup_blocks_next',uncertain_cleanup_blocks_new_grant)
 case('frame_truncation_idle_private_owner_survives',frame_fault_idle)
 case('frame_hardlink_idle_stops_without_retarget',lambda:frame_fault_idle(hardlink=True))
 case('frame_truncation_while_native_call_pending',frame_truncate_while_call_pending)
 report={'status':'PASS_SAME_PROCESS_OWNER_CHANNEL_FIXTURES','tests_run':len(results),'results':results,
         'helper_processes':Job.serial,'sanitizers':['address','undefined'],
         'real_unprivileged_kernel_peer_UID_PID_birth_checks':True,'cross_UID_root_peer_tested':False,
         'native_helper_executed':False,'administrator_or_camera_operations':0,'body_completion_or_recovery_proven':False,
         'build_receipt_sha256':sha256((HERE/'build-receipt-v2.json').read_bytes()).hexdigest(),
         'test_source_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
 with (HERE/'integration-results.json').open('x') as out:json.dump(report,out,indent=2);out.write('\n')
 print(json.dumps({k:v for k,v in report.items() if k!='results'}))

if __name__=='__main__':run_all()
