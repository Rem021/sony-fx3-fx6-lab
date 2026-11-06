"""Own parser and child IPC checks. Native IOKit executable is never run."""
from pathlib import Path
from hashlib import sha256
import json,subprocess,struct
import supervisor as S
import fixed_launch as P
import receipt_receiver as R
H=Path(__file__).resolve().parent;rows=[]
cmd=['/usr/bin/xcrun','clang','-std=c11','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(H/'descriptor_policy.c'),str(H/'descriptor_unit.c'),'-o',str(H/'artifacts/descriptor-unit')]
p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0,p.stderr
q=subprocess.run([cmd[-1]],capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
assert 'IOKit.framework'not in subprocess.check_output(['/usr/bin/otool','-L',cmd[-1]],text=True)
rows.append(dict(case='native_bounded_descriptor_parser',status='PASS',compile_argv=cmd,stdout=q.stdout,binary_sha256=sha256(Path(cmd[-1]).read_bytes()).hexdigest()))
for name,option,expected in [('descriptor-match',0,'HOST_RETURN_CAMERA_STATE_UNVERIFIED'),('descriptor-mismatch',33554432,'HOST_CONTROL_RETURN_CAPABILITY_UNTESTED'),('service-stall',4194304,'OWNER_RETAINED'),('cancel-between-OUT-IN',16777216,'OWNER_RETAINED')]:
    j=S.Job.fixture(name=name,fixture_option=option)
    try:
        value=j.wait(8);assert value['status']==expected,(value,j.error)
        f=j.flow_state
        if name=='descriptor-match':
            assert f.complete and not f.control_only and f.body_bytes==88
            assert f.descriptor and f.calls.get((0x0336,11))==1
        elif name=='descriptor-mismatch':
            assert f.complete and f.control_only and not f.body_bytes
            assert f.calls.get((0x0336,10))==1 and not any(f.calls.get((0x0336,k))for k in [1,2,3,4,5,6,7])
        elif name=='service-stall':
            assert f.calls.get((0x0336,2))==1 and not f.calls.get((0x0336,8))
        else:
            assert f.calls.get((0x0da1,2))==1 and not f.calls.get((0x0da1,3))
        if f.complete:
            assert (j.directory/'installed/entry.once.flow').read_bytes()==b''.join(j.flow_frames)
            j.runner.wait(timeout=4)
            guard=(j.directory/'global.journal').read_bytes();assert struct.unpack_from('<I',guard[-256:],20)[0]==3
        rows.append(dict(case=name,status='PASS',observed_status=value['status'],flow_frames=len(j.flow_frames),control_only=f.control_only,body_bytes=f.body_bytes,fixture_helper_sha256=j.expected_digest,directory=str(j.directory.relative_to(H))))
    finally:
        if j.runner.poll()is None:j.frame.fixture_gate(2)
        j.runner.wait(timeout=4);assert j.ipc.probe(j.verified.identity.pid)is None;j.close_observer()
        errors=(j.directory/'runner-stderr.txt').read_text()+(j.directory/'relay-stdout.txt').read_text();assert 'ERROR: AddressSanitizer'not in errors and 'runtime error:'not in errors
try:P.native_authority({})
except R.Rejected:pass
else:raise AssertionError('unreleased native authority accepted')
assert not P.JOB.exists()
with(H/'discovery-test-receipt.json').open('x')as f:json.dump(dict(status='NATIVE_DESCRIPTOR_POLICY_AND_OWN_CHILD_BRANCHES_PASS',checks=len(rows),rows=rows,actual_native_IOKit_or_root_executed=False,fixture_only=True),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status='PASS',checks=len(rows),branches=[r['case']for r in rows],native_executed=False)))
