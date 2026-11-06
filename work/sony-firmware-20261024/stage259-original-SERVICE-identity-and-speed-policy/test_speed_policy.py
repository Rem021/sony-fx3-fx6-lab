"""Target new original-derived speed policies only; no native USB or root."""
from pathlib import Path
from hashlib import sha256
import json,subprocess
import controller_ipc as I
import supervisor as S
H=Path(__file__).resolve().parent;rows=[]
cmd=['/usr/bin/xcrun','clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(H/'descriptor_policy.c'),str(H/'descriptor_unit.c'),'-o',str(H/'artifacts/descriptor-unit')]
q=subprocess.run(cmd,capture_output=True,text=True);assert q.returncode==0,q.stderr
q=subprocess.run([str(H/'artifacts/descriptor-unit')],capture_output=True,text=True,timeout=5)
assert q.returncode==0 and 'AddressSanitizer'not in q.stderr and 'runtime error:'not in q.stderr,(q.returncode,q.stdout,q.stderr)
rows.append(dict(case='three_original_derived_layouts_and_negative_SS_policy',status='PASS',stdout=q.stdout,compile_argv=cmd,binary_sha256=sha256((H/'artifacts/descriptor-unit').read_bytes()).hexdigest()))
for name,option,packet,length in [('derived-FS',134217728,64,46),('derived-SS',67108864,1024,70)]:
    j=S.Job.fixture(name=name,fixture_option=option)
    try:
        value=j.wait(4);assert value['status']=='HOST_RETURN_CAMERA_STATE_UNVERIFIED',value
        assert j.flow_state.complete and not j.flow_state.control_only and j.flow_state.body_bytes==88
        d=j.flow_state.descriptor
        assert int.from_bytes(d[4:8],'little')==length and int.from_bytes(d[52:54],'little')==packet
        j.runner.wait(timeout=3);assert not j.ipc.probe(j.verified.identity.pid)
        assert(Path(j.expected_path).parent/'entry.once.flow').read_bytes()==b''.join(j.flow_frames)
        rows.append(dict(case=name,status='PASS',raw_flow_frames=len(j.flow_frames),packet=packet,descriptor_bytes=length,child_gone=True,physical_identity_artificial=True))
    finally:
        if j.runner.poll()is None:j.request_stop();j.frame.fixture_gate(2);j.runner.wait(timeout=5)
        j.out.flush();j.err.flush()
        raw=(j.directory/'runner-stderr.txt').read_bytes()
        if(j.directory/'relay-stdout.txt').exists():raw+=(j.directory/'relay-stdout.txt').read_bytes()
        assert b'ERROR: AddressSanitizer'not in raw and b'runtime error:'not in raw
        j.close_observer()
with(H/'speed-policy-test-receipt.json').open('x')as f:
    json.dump(dict(status='ORIGINAL_DERIVED_SPEED_POLICY_OWN_CODE_CHECKS_PASS',checks=len(rows),rows=rows,
        actual_root_or_IOKit_or_original_Sony_code_executed=False,SERVICE_identity_problem_fixed=False),f,indent=2);f.write('\n')
print(json.dumps(dict(status='PASS',checks=len(rows),SERVICE_identity_fixed=False,actual_USB_operations=0)))
