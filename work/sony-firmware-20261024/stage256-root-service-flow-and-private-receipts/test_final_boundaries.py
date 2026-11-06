"""Regression for the final added per-call cooperative stop check."""
from pathlib import Path
import json,struct
import supervisor as S
H=Path(__file__).resolve().parent;rows=[]
for name,option,retained in [('normal-final',0,False),('stop-after-first-OUT',16777216,True)]:
    j=S.Job.fixture(name=name,fixture_option=option)
    try:
        value=j.wait(8)
        if retained:
            assert value['status']=='OWNER_RETAINED',(value,j.error)
            assert j.flow_state.calls.get((0x0da1,2))==1
            assert not j.flow_state.calls.get((0x0da1,3)) and not j.flow_state.calls.get((0x0336,1))
            assert not j.flow_state.calls.get((0x0da1,8)) and not j.flow_state.calls.get((0x0da1,9))
            assert not j.frame.snapshot().completed and j.runner.poll() is None
        else:
            assert value['status']=='HOST_RETURN_CAMERA_STATE_UNVERIFIED',(value,j.error)
            assert j.flow_state.complete and len(j.flow_frames)==80
            j.runner.wait(timeout=3)
            raw=(j.directory/'installed/entry.once.flow').read_bytes();assert raw==b''.join(j.flow_frames)
            guard=(j.directory/'global.journal').read_bytes();assert struct.unpack_from('<I',guard[-256:],20)[0]==3
            log=next(json.loads(x)for x in(j.directory/'relay-stdout.txt').read_text().splitlines()if x.startswith('{'))
            assert log['fixture_calls'][8:11]==[0,0,0] and log['fd_count_before']==log['fd_count_after']
        rows.append(dict(case=name,status='PASS',observed_status=value['status'],frames=len(j.flow_frames),fixture_helper_sha256=j.expected_digest,native_IOKit_executed=False,scope='real own child and Unix peer; artificial USB callbacks',directory=str(j.directory.relative_to(H))))
    finally:
        if j.runner.poll()is None:j.frame.fixture_gate(2)
        j.runner.wait(timeout=4)
        assert j.ipc.probe(j.verified.identity.pid) is None
        j.close_observer()
        errors=(j.directory/'runner-stderr.txt').read_text()
        if(j.directory/'relay-stdout.txt').exists():errors+=(j.directory/'relay-stdout.txt').read_text()
        assert 'ERROR: AddressSanitizer'not in errors and 'runtime error:'not in errors
with(H/'final-boundary-test-receipt.json').open('x')as f:json.dump(dict(status='FINAL_CURRENT_BUILD_NOMINAL_AND_COOPERATIVE_STOP_PASS',checks=2,rows=rows,new_root_or_camera_operations=0),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status='PASS',checks=2,observations=[x['observed_status']for x in rows],native_executed=False)))
