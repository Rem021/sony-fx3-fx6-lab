"""Real unprivileged helper/IPC tests; all camera objects are own fakes."""
from pathlib import Path
from hashlib import sha256
import json,os,struct,sys
sys.dont_write_bytecode=True
import supervisor as S
import receipt_receiver as R
H=Path(__file__).resolve().parent
assert len(sys.argv)==2 and sys.argv[1].startswith('attempt') and '/' not in sys.argv[1]
prefix=sys.argv[1]+'-'
rows=[];idle_record=None;idle_identity=None;idle_nonce=None;first_guard=None
for name,option,expected in [
    ('idle-five-second-no-service',16384,'HOST_IDLE_EXIT_CAMERA_STATE_UNKNOWN'),
    ('idle-wrong-service-anchor',268435456,'HOST_IDLE_EXIT_CAMERA_STATE_UNKNOWN'),
    ('service-object-still-held',4194304,'OWNER_RETAINED'),
    ('normal-controlled-port-flow',67108864,'HOST_RETURN_CONTROLLED_PORT_ASSOCIATION')]:
    j=S.Job.fixture(name=prefix+name,fixture_option=option)
    try:
        value=j.wait(8);assert value['status']==expected,value
        assert j.receipt is not None
        if expected=='HOST_IDLE_EXIT_CAMERA_STATE_UNKNOWN':
            assert value['helper_terminal_observed'] and not value['new_trial_authorized']
            assert j.receipt['phase']=='IDLE_HELD_EXIT' and j.flow_state.idle_held_exit_evidence()
            assert not j.flow_state.complete and not j.flow_state.body_bytes
            assert not any(pid==0x0336 for pid,op in j.flow_state.calls)
            assert j.runner.wait(timeout=3)==0
            guard=j.guard.read_bytes();assert len(guard)==512 and struct.unpack_from('<I',guard,276)[0]==3
            if first_guard is None:first_guard=j.guard
            idle_record=(j.directory/'private-record.bin').read_bytes()
            idle_identity=j.verified.identity;idle_nonce=j.frame.nonce
        elif expected=='OWNER_RETAINED':
            assert not value['helper_terminal_observed'] and not j.flow_state.idle_held_exit_evidence()
            assert j.ipc.probe(j.verified.identity.pid) is not None and j.receipt['phase']=='HELD'
            # Counterexample: changing only the final declaration cannot turn
            # a live SERVICE object into the source-disposed-only exit class.
            forged=bytearray((j.directory/'private-record.bin').read_bytes())
            struct.pack_into('<I',forged,12,3);forged[992:]=sha256(forged[:992]).digest()
            decoded=R.decode_record(bytes(forged),j.verified.identity,j.frame.nonce)
            assert decoded['phase']=='IDLE_HELD_EXIT'
            clone=S.Job();clone.receipt=None;clone.hello=True;clone.verified=j.verified;clone.frame=j.frame
            clone.ops=[];clone.responses=[];clone.flow_state=j.flow_state
            clone.directory=H/'runs'/(prefix+'saved-byte-service-object-counterexample');clone.directory.mkdir(mode=0o700)
            try:clone._message(bytes(forged))
            except R.Rejected as e:assert 'source-disposal-only' in str(e),e
            else:raise AssertionError('private declaration overrode held SERVICE flow')
            rows.append(dict(case='saved-byte-idle-declaration-cannot-override-held-SERVICE-flow',status='PASS',live_origin_recreated=False))
        else:
            assert j.receipt['phase']=='COMPLETE' and j.flow_state.complete and j.flow_state.body_bytes==88
            assert not j.flow_state.idle_held_exit_evidence()
        rows.append(dict(case=name,status='PASS',observed_status=value['status'],private_phase=j.receipt['phase'],
                         raw_frames=len(j.flow_frames),actual_camera=False,ordinary_user_kernel_peer_checked=True))
    finally:
        if j.runner.poll() is None:
            j.request_stop();j.frame.fixture_gate(2) # own fake-object termination gate only
        j.runner.wait(timeout=5);assert j.ipc.probe(j.verified.identity.pid) is None
        j.out.flush();j.err.flush()
        stderr=(j.directory/'runner-stderr.txt').read_bytes()+(j.directory/'relay-stdout.txt').read_bytes()
        assert b'ERROR: AddressSanitizer' not in stderr and b'runtime error:' not in stderr
        j.close_observer()

# Same host-only journal, different own fixture: UNKNOWN denies a new owner.
j=S.Job.fixture(name=prefix+'durable-unknown-denies-next-owner',fixture_option=67108864,guard=first_guard)
try:
    value=j.wait(4);assert value['status']=='DENIED_BEFORE_OWNER_ACTIONS',value
    assert value['helper_terminal_observed'] and not j.flow_frames and not j.receipt['result']['vendor_attempted']
    rows.append(dict(case='idle-exit-retains-durable-UNKNOWN-denial',status='PASS',observed_status=value['status']))
finally:
    assert j.runner.wait(timeout=3)==0;j.close_observer()

for name,offset,number in [('pending-host-call',192,1),('pending-wire-call',208,2),('cleared-retained-result',200,0),('relabeled-COMPLETE',12,1)]:
    bad=bytearray(idle_record);struct.pack_into('<I',bad,offset,number)
    bad[120:152]=sha256(bad[160:888]).digest();bad[992:]=sha256(bad[:992]).digest()
    try:R.decode_record(bytes(bad),idle_identity,idle_nonce)
    except R.Rejected:pass
    else:raise AssertionError(name+' accepted')
rows.append(dict(case='idle-private-record-pending-or-COMPLETE-forgeries-denied',status='PASS',variants=4,live_origin_recreated=False))

for call in [lambda:S.P.render_native('0'*32),lambda:S.P.native_authority({}),
             lambda:S.P.bootstrap('a','0'*64,'b','c','0'*32,fixture=False),
             lambda:S.P.command('x',H,'0'*32,fixture=False)]:
    try:call()
    except R.Rejected:pass
    else:raise AssertionError('offline native render unexpectedly open')
rows.append(dict(case='native-authority-render-command-and-bootstrap-remain-closed',status='PASS'))
result=dict(status='COOPERATIVE_IDLE_EXIT_OWN_PROCESS_REGRESSIONS_PASS',checks=len(rows),rows=rows,
            native_helper_executed=False,new_root_or_USB_operations=0,
            real_camera_return_or_recovery_proven=False,old_trial262_not_replayed=True)
with (H/'test-receipt.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
