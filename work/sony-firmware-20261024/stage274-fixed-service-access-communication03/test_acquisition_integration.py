"""Real ordinary-user helper/IPC, with artificial SERVICE acquisition faults."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,struct,subprocess,sys
sys.dont_write_bytecode=True
import supervisor as S
import receipt_receiver as R
import flow_receiver as F
import fixed_launch as P
H=Path(__file__).resolve().parent
assert not P.JOB.exists()
rows=[];saved=None
for step,option in [(203,32768),(210,65536)]:
    d=H/'runs'/('acq-'+str(step)+'-seed');d.mkdir(mode=0o700)
    guard=d/'old.journal';spec=d/'recovery.bin'
    seed=subprocess.Popen([str(H/'artifacts/recovery-seed'),str(guard),str(spec),'0'],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    assert seed.stdout.readline()=='ready\n';seed.stdin.write('x');seed.stdin.flush();assert seed.wait(timeout=3)==0
    before=guard.read_bytes()
    j=S.Job.fixture(name='acq-'+str(step),fixture_option=option,guard=guard,recovery_spec=spec)
    try:
        result=j.wait(4);assert result['status']=='OWNER_RETAINED',result
        assert not result['bounded_service_read_observed'] and j.receipt['phase']=='HELD'
        assert j.receipt['manual_recovery']['stage']==2 and not j.error
        acquisition=j.flow_state.acquisition
        assert acquisition['step']==step and acquisition['raw_return']==(-536870210 if step==203 else -536870203)
        assert j.flow_state.pending is None and not j.flow_state.complete
        assert j.flow_state.calls[(0x0336,11)]==1
        assert not any((0x0336,n)in j.flow_state.calls for n in [1,2,3,4,5,6,7,8,10])
        assert guard.read_bytes()[:len(before)]==before and len(guard.read_bytes())==3*256
        assert j.ipc.probe(j.verified.identity.pid)is not None
        saved=(list(j.flow_frames),j.verified.identity,bytes(j.frame.nonce))
        rows.append(dict(case='full-IPC-acquisition-failure-'+str(step),status='PASS',
            metadata=acquisition,frames=len(j.flow_frames),kernel_peer_and_private_RCPT5_checked=True,
            artificial_device_and_cache=True,no_SERVICE_auth_or_read_or_STOP=True))
    finally:
        # Only this artificial fixture has a termination gate. No signal,
        # USB cleanup, recovery command or production exit is inferred.
        j.frame.fixture_gate(2);assert j.runner.wait(timeout=5)==90
        assert j.ipc.probe(j.verified.identity.pid)is None
        j.out.flush();j.err.flush()
        assert b'ERROR: AddressSanitizer'not in (j.directory/'relay-stdout.txt').read_bytes()
        assert b'runtime error:'not in (j.directory/'relay-stdout.txt').read_bytes()
        j.close_observer()

frames,identity,nonce=saved
receiver=F.FlowReceiver(identity,nonce,R.GRANT_ID)
for frame in frames[:-1]:receiver.accept(frame)
bad=bytearray(frames[-1]);struct.pack_into('<I',bad,592,203)
bad[640:]=sha256(bad[:640]).digest()
try:receiver.accept(bytes(bad))
except R.Rejected:pass
else:raise AssertionError('post-acquisition substep replacement accepted')
rows.append(dict(case='saved-post-return-acquisition-substitution-denied',status='PASS',live_origin_recreated=False))

old=H.parent/'stage268-fixed-manual-recovered-communication02/flow_receiver.py'
spec=importlib.util.spec_from_file_location('old_flow_receiver_v3',old)
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
old_receiver=legacy.FlowReceiver(identity,nonce,R.GRANT_ID)
try:old_receiver.accept(frames[0])
except R.Rejected:pass
else:raise AssertionError('legacy v3 receiver accepted new protocol')
rows.append(dict(case='old-reader-rejects-new-v5',status='PASS'))

try:P.native_authority({})
except R.Rejected:pass
else:raise AssertionError('unapproved authority accepted')
assert not P.JOB.exists()
rows.append(dict(case='new-live-authority-denied-and-job-not-staged',status='PASS'))
result=dict(status='FULL_CONTROLLER_V5_ACQUISITION_FAILURE_IPC_PASS',rows=rows,
    native_helper_executed=False,actual_root_journal_modified=False,new_root_or_USB_operations=0,
    no_existing_process_signalled=True,whole_real_camera_flow_proven=False)
with (H/'acquisition-integration-check.json').open('x')as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status=result['status'],groups=len(rows),new_root_or_USB_operations=0)))
