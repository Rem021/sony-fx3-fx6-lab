"""Real own child/AF_UNIX IPC, artificial USB callbacks, no IOKit/root API."""
from pathlib import Path
from hashlib import sha256
import ctypes as C,json,os,struct,time
import supervisor as S
import controller_ipc as I
import receipt_receiver as R
import fixed_launch as P
from flow_receiver import FlowReceiver
H=Path(__file__).resolve().parent;rows=[]
assert os.getuid()==os.geteuid()!=0

def reject(fn):
    try:fn()
    except (R.Rejected,ValueError):return
    raise AssertionError('bad flow accepted')

def saved_nominal():
    d=H/'runs/integration-normal-initial';proof=json.loads((d/'verified-helper.json').read_text());identity=R.Identity(**proof['identity'])
    frames=[p.read_bytes()for p in sorted(d.glob('flow-*.bin'))];f=FlowReceiver(identity,bytes.fromhex(proof['nonce']),R.GRANT_ID)
    for frame in frames:f.accept(frame)
    assert f.complete and len(frames)==80
    assert b''.join(frames)==(d/'installed/entry.once.flow').read_bytes()
    assert I.IPC().probe(identity.pid) is None
    result=R.decode_record((d/'received-final-record.bin').read_bytes(),identity,bytes.fromhex(proof['nonce']))
    assert result['result']['vendor_attempted']==1 and result['result']['wire_pending']==0
    log=next(json.loads(x)for x in (d/'relay-stdout.txt').read_text().splitlines()if x.startswith('{'))
    assert log['fixture_calls'][8:11]==[0,0,0] and log['fd_count_before']==log['fd_count_after']
    # Global finish records camera-state UNKNOWN even on nominal host return.
    guard=(d/'global.journal').read_bytes();assert struct.unpack_from('<I',guard[-256:],20)[0]==3
    rows.append(dict(case='completed_nominal_child_recovered_not_replayed',status='PASS',frames=80,root_journal_equals_parent_raw=True,legacy_cleanup_callbacks=0,helper_gone=True,global_camera_state='UNKNOWN',directory=str(d.relative_to(H))))
    return frames,proof,identity

def partial_failure():
    j=S.Job.fixture(name='service-write-stall',fixture_option=4194304)
    try:
        value=j.wait(7);assert value['status']=='OWNER_RETAINED',(value,j.error)
        f=j.flow_state;assert not f.complete and f.terminal and f.calls.get((0x0336,2))==1
        assert not f.calls.get((0x0336,8)) and not f.calls.get((0x0da1,9))
        assert any(r['raw_return']==-99 for r in f.rows)
        assert j.frame.snapshot().completed==0 and j.runner.poll() is None
        rows.append(dict(case='service_failure_retains_original_child_without_legacy_cleanup',status='PASS',frames=f.count,observed_status=value['status'],service_OUT_attempts=1,service_disposals=0,driver_return_attempts=0,native_completed=False,directory=str(j.directory.relative_to(H))))
    finally:
        # Explicit teardown gate exists only in the no-IOKit fixture binary.
        # It does not simulate recovery or authorize termination of real I/O.
        if j.runner.poll()is None:j.frame.fixture_gate(2)
        j.runner.wait(timeout=4);j.close_observer()

def bad_hello():
    j=S.Job.fixture(name='wrong-self-image')
    original=j._hello
    def corrupt(data):
        a=bytearray(data);a[88]^=1;a[128:]=sha256(a[:128]).digest();original(bytes(a))
    j._hello=corrupt
    try:
        value=j.wait(4);assert value['status']=='UNKNOWN_OBSERVER_ERROR' and not j.receiver.acknowledged
        assert not j.guard.exists() and j.frame.snapshot().started==0
        j.runner.wait(timeout=4)
        rows.append(dict(case='wrong_helper_image_stops_before_owner_or_flow',status='PASS',native_started=False,global_guard_created=False,directory=str(j.directory.relative_to(H))))
    finally:
        assert j.runner.poll()is not None
        j.close_observer()

def frame_mutations(frames,proof,identity):
    cases=[]
    def check(name,index,fn):
        f=FlowReceiver(identity,bytes.fromhex(proof['nonce']),R.GRANT_ID)
        for raw in frames[:index]:f.accept(raw)
        raw=bytearray(frames[index]);fn(raw);raw[480:]=sha256(raw[:480]).digest()
        reject(lambda:f.accept(bytes(raw)));cases.append(name)
    check('nonce',1,lambda b:b.__setitem__(56,b[56]^1))
    check('helper_birth',1,lambda b:b.__setitem__(40,b[40]^1))
    check('sequence',1,lambda b:struct.pack_into('<Q',b,16,999))
    check('previous_hash',1,lambda b:b.__setitem__(448,b[448]^1))
    check('unmatched_return',2,lambda b:struct.pack_into('<I',b,24,2))
    check('return_subject_changed',2,lambda b:b.__setitem__(160,b[160]^1))
    check('invented_proof_field',1,lambda b:b.__setitem__(304,1))
    check('incomplete_success',79,lambda b:struct.pack_into('<I',b,140,0))
    f=FlowReceiver(identity,bytes.fromhex(proof['nonce']),R.GRANT_ID)
    b=bytearray(frames[-1]);struct.pack_into('<Q',b,16,1);b[448:480]=bytes(32);b[480:]=sha256(b[:480]).digest();reject(lambda:f.accept(bytes(b)));cases.append('completion_without_native_call_chain')
    rows.append(dict(case='new_flow_corruption_and_incomplete_result_rejected',status='PASS',rejections=cases))

def old_scope_and_authority(frames,proof,identity):
    d=H/'runs/integration-normal-initial';b=bytearray((d/'received-final-record.bin').read_bytes());b[:8]=b'FX3RCPT1';struct.pack_into('<I',b,8,1);b[992:]=sha256(b[:992]).digest()
    reject(lambda:R.decode_record(bytes(b),identity,bytes.fromhex(proof['nonce'])))
    ipc=I.IPC();buf=(C.c_ubyte*4096)();nonce=b'N'*16
    assert ipc.fx3_entry_init(buf,4096,1,os.getuid(),nonce,b'K'*32,b'A'*32)==0
    g=I.Grant.from_buffer(buf,ipc.grant_offset);assert(g.schema,g.scope)==(4,0x53564332)
    g.scope=0x55534232;claim=ipc.lib.fx3_entry_claim;claim.restype=C.c_int;claim.argtypes=[C.c_void_p,C.c_void_p];assert claim(buf,nonce)!=0
    reject(lambda:P.native_authority({}))
    assert '#define FX3_SERVICE_PROFILE_READY 0'in(H/'service_profile.h').read_text()
    assert not P.JOB.exists()
    rows.append(dict(case='old_scope_old_receipt_and_unreleased_native_factory_denied',status='PASS',native_staged=False,native_executed=False))

try:
    frames,proof,identity=saved_nominal();partial_failure();bad_hello();frame_mutations(frames,proof,identity);old_scope_and_authority(frames,proof,identity)
    for d in(H/'runs').iterdir():
        if d.is_dir():
            for name in['runner-stderr.txt','relay-stdout.txt']:
                p=d/name
                if p.exists():assert 'ERROR: AddressSanitizer'not in p.read_text()and'runtime error:'not in p.read_text()
except Exception as e:
    with(H/'integration-test-failure-v2.json').open('x')as f:json.dump(dict(error=repr(e),passed=rows),f,ensure_ascii=False,indent=2)
    raise
with(H/'integration-test-receipt.json').open('x')as f:json.dump(dict(status='OWN_NATIVE_CHILD_IPC_AND_RAW_FLOW_RECEIPTS_PASS',checks=len(rows),rows=rows,root_or_USB_operations=0,actual_IOKit_native_executed=False,artificial_pipe_callbacks_only=True),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status='PASS',checks=len(rows),rows=[r['case']for r in rows],native_executed=False)))
