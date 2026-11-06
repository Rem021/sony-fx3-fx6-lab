"""Only the changed location constant; own fake-owner processes, no USB."""
from pathlib import Path
import json,struct
import supervisor as S
import fixed_launch as P
H=Path(__file__).resolve().parent
cache=json.loads((H/'current-cache-target.json').read_text())
assert cache['candidate_count']==1
location=cache['candidates'][0]['locationID'];assert location==P.TARGET['locationID']==0x01100000
rows=[]
for swapped in (False,True):
 j=S.Job.fixture(fixture_option=8192 if swapped else 0)
 try:
  value=j.wait(3);assert value['status']=='HOST_RETURN_OBSERVED',value
  assert len(j.responses)==3 and all(r['status']==0 for r in j.responses)
  result=j.receipt['result_bytes'];before,after=struct.unpack_from('<I',result,84)[0],struct.unpack_from('<I',result,148)[0]
  assert before==after==location
  profile=struct.unpack_from('<8I',result,184);assert profile[6:]==((2,1) if swapped else (1,2))
  j.runner.wait(timeout=3);j.out.flush()
  log=next(json.loads(x) for x in (j.directory/'relay-stdout.txt').read_text().splitlines() if x.startswith('{') and 'wire_calls' in x)
  assert log['wire_calls']==[0,0,0]
  rows.append(dict(case='current_port_swapped_pipes' if swapped else 'current_port',status='PASS',
   directory=str(j.directory.relative_to(H)),location_hex=f'0x{location:08x}',wire_calls=log['wire_calls']))
 finally:
  if j.runner.poll() is None:j.request_stop();j.frame.fixture_gate(2)
  j.runner.wait(timeout=5);j.out.flush();j.err.flush()
  assert b'ERROR: AddressSanitizer' not in (j.directory/'runner-stderr.txt').read_bytes()+(j.directory/'relay-stdout.txt').read_bytes()
  j.close_observer()
with (H/'current-port-verification.json').open('x') as f:json.dump(dict(status='OWN_PROCESS_CURRENT_PORT_AND_PIPE_MAP_SCOPED_PASS',rows=rows,checks=2,new_admin_or_USB_operations=0),f,indent=2)
print(json.dumps(dict(checks=2,current_port=f'0x{location:08x}',new_admin_or_USB_operations=0)))
