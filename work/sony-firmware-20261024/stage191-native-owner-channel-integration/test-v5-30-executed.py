"""Real unprivileged peers + same-process SDK-shaped fake owner integration.

Refuses the native artifact. Never launches sudo/Terminal/IOKit/camera code.
All files are new project-local fixtures; cleanup only our live socket nodes.
"""
from pathlib import Path
from hashlib import sha256
import array, contextlib, ctypes as C, json, mmap, os, plistlib, secrets, socket, struct, subprocess, time, traceback
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOCKET_ROOT=ROOT/'work/ipc191'
BUILD=json.loads((HERE/'build-receipt-v5.json').read_text())
HELPER=Path(BUILD['builds']['fixture']['path'])
assert HELPER.name=='owner-fixture-helper' and sha256(HELPER.read_bytes()).hexdigest()==BUILD['builds']['fixture']['sha256']
assert 'IOKit.framework' not in BUILD['builds']['fixture']['dependencies']
assert not BUILD['native_build_released'] and not BUILD['native_helper_executed']
assert os.getuid()==os.geteuid()!=0
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
for m in BUILD['sources']:assert sha256((HERE/m['path']).read_bytes()).hexdigest()==m['sha256']
LIB=C.CDLL(BUILD['builds']['ipc']['path'])
def function(name,result,args):
 f=getattr(LIB,name);f.restype=result;f.argtypes=args;return f
init=function('fx3_entry_init',C.c_int,[C.c_void_p,C.c_size_t,C.c_uint32,C.c_uint32,C.c_void_p,C.c_void_p,C.c_void_p])
fields=function('fx3_entry_fixture_fields',C.c_int,[C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint64,C.c_uint64])
pid_info=function('fx3_entry_pid_info',C.c_int,[C.c_uint32,C.POINTER(C.c_uint32),C.POINTER(C.c_uint64),C.POINTER(C.c_uint64)])
layout=function('fx3_entry_layout',C.c_uint32,[C.c_uint32])
ipc_layout=function('fx3_ipc_layout',C.c_uint32,[C.c_uint32])
ready=function('fx3_entry_ready',C.c_uint32,[C.c_void_p]);ack=function('fx3_entry_ack',None,[C.c_void_p])
completed=function('fx3_entry_completed',C.c_uint32,[C.c_void_p]);value=function('fx3_entry_value',C.c_uint64,[C.c_void_p,C.c_uint32])
gate=function('fx3_entry_fixture_gate',None,[C.c_void_p,C.c_uint32]);stop=function('fx3_ipc_stop',None,[C.c_void_p])

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
 def __init__(self,option=0,block=0,fail=0,observed=b'A'*32):
  Job.serial+=1;self.name=f'{Job.serial:03d}-{secrets.token_hex(3)}'
  self.path=HERE/'runs'/self.name;self.path.mkdir(mode=0o700)
  SOCKET_ROOT.mkdir(mode=0o700,exist_ok=True);self.sockdir=SOCKET_ROOT/self.name;self.sockdir.mkdir(mode=0o700)
  self.sockpath=self.sockdir/'s';assert len(os.fsencode(self.sockpath))<104
  self.server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.server.bind(str(self.sockpath));os.chmod(self.sockpath,0o600);self.server.listen(1);self.server.settimeout(4)
  self.conn=None;self.proc=None;self.record=None;self.held=False;self.expected_wire=None;self.expected_pipes=None;self.forced_fixture_exit=False
  fd=os.open(self.path/'shared.bin',os.O_RDWR|os.O_CREAT|os.O_EXCL,0o600);os.fchmod(fd,0o600);os.ftruncate(fd,4096)
  self.mm=mmap.mmap(fd,4096);os.close(fd);self.buf=(C.c_ubyte*4096).from_buffer(self.mm);self.ptr=C.addressof(self.buf)
  self.grant=Grant.from_buffer(self.mm,layout(1));self.nonce=secrets.token_bytes(16);self.id=0
  assert init(self.ptr,4096,1,os.getuid(),self.nonce,b'K'*32,b'A'*32)==0
  uid=C.c_uint32();sec=C.c_uint64();usec=C.c_uint64();assert pid_info(os.getpid(),C.byref(uid),C.byref(sec),C.byref(usec))==0
  assert uid.value==os.getuid()
  assert fields(self.ptr,fail,option,block,observed,os.getpid(),sec.value,usec.value)==0
  self.argv=[str(HELPER),str(self.path/'shared.bin'),self.nonce.hex(),str(self.path/'entry.once'),str(self.sockpath)]
  self.proc=subprocess.Popen(self.argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  wait(lambda: ready(self.ptr) or self.proc.poll() is not None)
  assert ready(self.ptr),self.proc.communicate()
  assert self.grant.pid==self.proc.pid
  ack(self.ptr)
  self.conn,_=self.server.accept();self.conn.settimeout(4)
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
  self.record=json.loads(out);assert self.record['native_return']==expected,self.record
  assert self.record['fd_count_before']==self.record['fd_count_after'],self.record
  assert not self.record['physical_camera_acceptance']
  result=bytes(self.mm[ipc_layout(1):ipc_layout(1)+layout(4)])
  assert sha256(result).hexdigest()==self.record['result_sha256'],self.record
  return self.record
 def retain(self):
  wait(lambda:value(self.ptr,2)==1)
  self.held=True;assert not completed(self.ptr) and self.proc.poll() is None
  assert value(self.ptr,3)==3 and value(self.ptr,5)==1
  return self
 def close(self):
  if self.conn:self.conn.close();self.conn=None
  self.server.close()
  if self.proc and self.proc.poll() is None:
   gate(self.ptr,1);time.sleep(.08);gate(self.ptr,2)
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
  del self.grant;del self.buf;self.mm.close()
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
report={'status':'PASS_SAME_PROCESS_OWNER_CHANNEL_FIXTURES','tests_run':len(results),'results':results,
        'helper_processes':Job.serial,'sanitizers':['address','undefined'],
        'real_unprivileged_kernel_peer_UID_PID_birth_checks':True,'cross_UID_root_peer_tested':False,
        'native_helper_executed':False,'administrator_or_camera_operations':0,'body_completion_or_recovery_proven':False,
        'build_receipt_sha256':sha256((HERE/'build-receipt-v5.json').read_bytes()).hexdigest(),
        'test_source_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
with (HERE/'integration-results.json').open('x') as out:json.dump(report,out,indent=2);out.write('\n')
print(json.dumps({k:v for k,v in report.items() if k!='results'}))
