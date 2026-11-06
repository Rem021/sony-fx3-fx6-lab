"""Changed integration only: own Mac processes and fake SDK objects, never USB."""
from pathlib import Path
from contextlib import contextmanager
from hashlib import sha256
import json,os,struct,time,traceback
import supervisor as S
import receipt_receiver as R
H=Path(__file__).resolve().parent
rows=[]

@contextmanager
def job(**kw):
 j=S.Job.fixture(**kw)
 try:yield j
 finally:
  if j.runner.poll() is None:
   j.request_stop();j.frame.fixture_gate(2)  # only this test's own fake-call gate
  j.runner.wait(timeout=5)
  if j.relay is not j.runner:j.relay.wait(timeout=2)
  j.out.flush();j.err.flush()
  logs=(j.directory/'runner-stderr.txt').read_bytes()
  if (j.directory/'relay-stdout.txt').exists():logs+=(j.directory/'relay-stdout.txt').read_bytes()
  assert b'ERROR: AddressSanitizer' not in logs and b'runtime error:' not in logs
  j.close_observer()

def output(j):
 values=[json.loads(x) for x in (j.directory/'relay-stdout.txt').read_text().splitlines() if x.startswith('{')]
 return next(x for x in values if 'wire_calls' in x)

def await_exit(j):
 j.runner.wait(timeout=4);j.out.flush()
 for _ in range(30):
  value=j.step(.005)
  if value.get('helper_terminal_observed'):break
  time.sleep(.002)
 return value

def normal(reverse=False):
 with job(fixture_option=8192 if reverse else 0) as j:
  value=j.wait(3);assert value['status']=='HOST_RETURN_OBSERVED',value
  assert len(j.responses)==3 and [x['id'] for x in j.responses]==[1,2,3]
  assert all(x['status']==0 and not x['flags']&(1|2|32) for x in j.responses)
  assert j.hello['image_sha256']==j.expected_digest and j.receipt['transport_peer_verified']
  assert j.receipt['native_return']==0 and j.receipt['result']['vendor_attempted']==0
  profile=struct.unpack_from('<8I',j.receipt['result_bytes'],184)
  assert profile[6:]==((2,1) if reverse else (1,2)),profile
  await_exit(j);log=output(j);assert log['wire_calls']==[0,0,0]
  rows.append(dict(case='swapped_pipe_map' if reverse else 'observe_status_end',status='PASS',
    path=str(j.directory.relative_to(H)),responses=len(j.responses),wire_calls=log['wire_calls'],profile=list(profile)))

def custom_requests(j,ops,bad_nonce=False):
 def hello(data):
  j.hello=j.receiver.accept_hello(data);j.receiver.acknowledge();j.ops=ops
  nonce=bytes([j.frame.nonce[0]^1])+j.frame.nonce[1:] if bad_nonce else j.frame.nonce
  for n,(op,payload) in enumerate(ops,1):
   packet=struct.pack('<IIQQQII16s',0x31385146,1,n,17,j.entry_ack_ns+500_000_000,op,len(payload),nonce)+payload.ljust(516,b'\0')
   assert len(packet)==572
   j.conn.sendall(struct.pack('<I',572)+packet)
 j._hello=hello

def forbidden(op,payload):
 with job() as j:
  custom_requests(j,[(op,payload)])
  value=j.wait(3);assert value['status']=='HOST_ABORT_RETURN_OBSERVED',value
  assert j.receipt['native_return']==1 and j.responses==[]
  assert j.receipt['result']['vendor_attempted']==0
  await_exit(j);log=output(j);assert log['wire_calls']==[0,0,0]
  rows.append(dict(case={2:'reject_START',3:'reject_AUTH',4:'reject_STOP'}[op],status='PASS',
    path=str(j.directory.relative_to(H)),wire_calls=log['wire_calls'],outcome=value['status']))

def wrong_nonce():
 with job() as j:
  custom_requests(j,[(6,b'')],bad_nonce=True)
  value=j.wait(3);assert value['status']=='HOST_ABORT_RETURN_OBSERVED',value
  assert len(j.responses)==1 and j.responses[0]['status']==1
  await_exit(j);log=output(j);assert log['wire_calls']==[0,0,0]
  rows.append(dict(case='wrong_session_nonce',status='PASS',path=str(j.directory.relative_to(H)),wire_calls=log['wire_calls']))

def wrong_image():
 with job() as j:
  original=j._hello
  def corrupt(data):
   changed=bytearray(data);changed[88]^=1;changed[128:]=sha256(changed[:128]).digest();original(bytes(changed))
  j._hello=corrupt
  value=j.wait(3);assert value['status']=='UNKNOWN_OBSERVER_ERROR',value
  assert not j.receiver.acknowledged and not j.guard.exists()
  j.runner.wait(timeout=4);log=output(j)
  assert log['wire_calls']==[0,0,0] and all(x==0 for x in log['fixture_calls'])
  rows.append(dict(case='wrong_image_before_owner',status='PASS',path=str(j.directory.relative_to(H)),wire_calls=log['wire_calls']))

def pending_call():
 with job(block=7) as j:
  value=j.wait(.2);assert value['status']=='OWNER_ALIVE_UNRESOLVED',value
  pid=j.verified.identity.pid;assert j.ipc.probe(pid) is not None
  # A user-writable completion flag cannot replace the live peer's final record.
  os.pwrite(j.frame.fd,struct.pack('<I',1),j.ipc.grant_offset+S.I.Grant.completed.offset)
  value=j.wait(.08);assert value['status']=='OWNER_ALIVE_UNRESOLVED' and j.receipt is None,value
  j.request_stop();j.frame.fixture_gate(1)
  value=j.wait(3);assert value['status']=='HOST_ABORT_RETURN_OBSERVED',value
  await_exit(j);log=output(j);assert log['wire_calls']==[0,0,0]
  rows.append(dict(case='pending_owner_cannot_fake_completion',status='PASS',path=str(j.directory.relative_to(H)),wire_calls=log['wire_calls']))

tests=[('observe_status_end',lambda:normal(False)),('swapped_pipe_map',lambda:normal(True)),
 ('reject_START',lambda:forbidden(2,bytes.fromhex('4301ff37aad70000'))),
 ('reject_AUTH',lambda:forbidden(3,bytes.fromhex('fffe0000')+bytes(512))),
 ('reject_STOP',lambda:forbidden(4,bytes.fromhex('430100c855280000'))),
 ('wrong_session_nonce',wrong_nonce),('wrong_image_before_owner',wrong_image),
 ('pending_owner_cannot_fake_completion',pending_call)]
for name,test in tests:
 try:test()
 except Exception as exc:
  with (H/'integration-failure.json').open('x') as f:json.dump(dict(failed_case=name,error=repr(exc),traceback=traceback.format_exc(),passed_rows=rows),f,indent=2)
  raise
 with (H/'runs'/(name+'.json')).open('x') as f:json.dump(rows[-1],f,indent=2)
 print(name+': PASS',flush=True)
receipt=dict(status='OWN_PROCESSES_SHARED_TRANSPORT_STATUS_ONLY_SCOPED_PASS',checks=len(rows),rows=rows,
 native_helper_executed=False,new_root_or_camera_operations=0,
 own_fixture_callbacks_not_real_IOKit_driver_or_device_acceptance=True,
 original_Sony_or_kernel_code_executed=False,previous_model_suites_repeated=False)
with (H/'integration-receipt.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
