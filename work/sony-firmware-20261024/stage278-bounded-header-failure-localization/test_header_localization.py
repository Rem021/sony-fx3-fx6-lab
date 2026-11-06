"""Full ordinary-user helper/IPC integration for bounded read0 header localization."""
from pathlib import Path
from hashlib import sha256
import json,struct,subprocess,sys
sys.dont_write_bytecode=True
import supervisor as S
import receipt_receiver as R
import flow_receiver as F
import fixed_launch as P
H=Path(__file__).resolve().parent
assert not P.JOB.exists()

def header_option(variant):
    assert 0<=variant<=15
    return ((variant&3)<<18)|(((variant>>2)&3)<<10)|67108864

cases=[
    ('hdr-short-count',1,2,0,(),'short_count',12,11,0),
    ('hdr-size-mismatch',2,3,0x01,('size',),'size_mismatch',12,12,0),
    ('hdr-pfunc-mismatch',3,4,0x02,('pFunc',),'pfunc_mismatch',12,12,0),
    ('hdr-sequence-mismatch',4,5,0x04,('sequence',),'sequence_mismatch',12,12,0),
    ('hdr-version-mismatch',5,6,0x08,('version',),'version_mismatch',12,12,0),
    ('hdr-micon-mismatch',6,7,0x10,('miconType',),'micon_mismatch',12,12,0),
    ('hdr-offset-mismatch',7,8,0x20,('offsetType',),'offset_mismatch',12,12,0),
    ('hdr-response-mismatch',8,9,0x40,('response',),'response_mismatch',12,12,0),
    ('hdr-multiple-mismatch',9,10,0x49,('size','version','response'),'multiple_mismatch',12,12,0),
    ('hdr-op5-io-error',10,0,0,(),'not_evaluated',6,0,-536870199),
]
rows=[];saved=None
for name,variant,exp_reason,exp_mask,exp_fields,exp_name,exp_op5_status_or_len,exp_count,exp_raw in cases:
    d=H/'runs'/(name+'-seed');d.mkdir(mode=0o700)
    guard=d/'old.journal';spec=d/'recovery.bin'
    seed=subprocess.Popen([str(H/'artifacts/recovery-seed'),str(guard),str(spec),'0'],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    assert seed.stdout.readline()=='ready\n';seed.stdin.write('x');seed.stdin.flush();assert seed.wait(timeout=3)==0
    before=guard.read_bytes()
    j=S.Job.fixture(name=name,fixture_option=header_option(variant),guard=guard,recovery_spec=spec)
    try:
        result=j.wait(4);assert result['status']=='OWNER_RETAINED',result
        assert not result['bounded_service_read_observed'] and j.receipt['phase']=='HELD'
        assert j.receipt['manual_recovery']['stage']==2 and not j.error
        hdr=j.flow_state.read0_header
        assert hdr==dict(reason=exp_reason,name=exp_name,mask=exp_mask,fields=exp_fields),hdr
        assert j.flow_state.pending is None and not j.flow_state.complete and j.flow_state.body_bytes==0
        assert j.flow_state.calls[(0x0336,11)]==1 and j.flow_state.calls[(0x0336,1)]==1
        assert j.flow_state.calls[(0x0336,2)]==7 and j.flow_state.calls[(0x0336,3)]==7
        assert j.flow_state.calls[(0x0336,4)]==1 and j.flow_state.calls[(0x0336,5)]==1
        assert not any((0x0336,n)in j.flow_state.calls for n in [6,7,8,10])
        op5_return=[r for r in j.flow_state.rows if r['op']==5 and r['point']==1]
        held_row=[r for r in j.flow_state.rows if r['op']==51 and r['point']==3]
        assert len(op5_return)==1 and len(held_row)==1
        assert op5_return[0]['read0_header']==hdr and held_row[0]['read0_header']==hdr
        assert op5_return[0]['count']==exp_count and op5_return[0]['raw_return']==exp_raw
        assert op5_return[0]['status']==(6 if variant==10 else 0)
        # Ensure private journal on disk matches socket frames byte-for-byte.
        disk_flow=(j.directory/'installed/entry.once.flow').read_bytes()
        assert disk_flow==b''.join(j.flow_frames)
        assert guard.read_bytes()[:len(before)]==before and len(guard.read_bytes())==3*256
        assert j.ipc.probe(j.verified.identity.pid)is not None
        if variant==5:
            saved=(list(j.flow_frames),j.verified.identity,bytes(j.frame.nonce))
        rows.append(dict(case=name,status='PASS',read0_header=hdr,frames=len(j.flow_frames),
            kernel_peer_and_private_RCPT5_checked=True,no_body_read_or_STOP_after_header_reject=True,
            raw_header_or_HASP_bytes_exported=False,artificial_device_and_cache=True))
    finally:
        j.frame.fixture_gate(2);assert j.runner.wait(timeout=5)==90
        assert j.ipc.probe(j.verified.identity.pid)is None
        j.out.flush();j.err.flush()
        assert b'ERROR: AddressSanitizer'not in (j.directory/'relay-stdout.txt').read_bytes()
        assert b'runtime error:'not in (j.directory/'relay-stdout.txt').read_bytes()
        j.close_observer()

frames,identity,nonce=saved
# 1) Reject post-return mutation of read0_header reason/mask on terminal HELD frame.
for label,patch in [
    ('post-return-reason-cleared',lambda b:struct.pack_into('<BB',b,213,0,0)),
    ('post-return-reason-swapped-to-ok',lambda b:struct.pack_into('<BB',b,213,1,0)),
    ('post-return-reason-swapped-to-size',lambda b:struct.pack_into('<BB',b,213,3,1)),
    ('reserved-byte-nonzero',lambda b:struct.pack_into('<B',b,215,1)),
    ('premature-body-bytes-on-held',lambda b:struct.pack_into('<I',b,208,88)),
]:
    receiver=F.FlowReceiver(identity,nonce,R.GRANT_ID)
    for frame in frames[:-1]:receiver.accept(frame)
    bad=bytearray(frames[-1]);patch(bad);bad[640:]=sha256(bad[:640]).digest()
    try:receiver.accept(bytes(bad))
    except R.Rejected:pass
    else:raise AssertionError(label+' accepted')

# 2) Reject premature header reason on op=5, point=0 (frame index -3).
receiver=F.FlowReceiver(identity,nonce,R.GRANT_ID)
for frame in frames[:-3]:receiver.accept(frame)
bad_before=bytearray(frames[-3]);struct.pack_into('<BB',bad_before,213,6,8)
bad_before[640:]=sha256(bad_before[:640]).digest()
try:receiver.accept(bytes(bad_before))
except R.Rejected:pass
else:raise AssertionError('premature header reason on op=5 point=0 accepted')

# 3) Direct unit checks on read0_header_record shape invariants.
raw=bytearray(672);raw[:8]=b'FX3FLOW6'
for label,op,point,status,returned,known,count,r_byte,m_byte,res_byte in [
    ('reason-out-of-range',5,1,0,1,1,12,11,0,0),
    ('mask-out-of-range',5,1,0,1,1,12,10,0x80,0),
    ('ok-with-mask',5,1,0,1,1,12,1,0x08,0),
    ('short-with-mask',5,1,0,1,1,11,2,0x01,0),
    ('single-reason-wrong-bit',5,1,0,1,1,12,6,0x01,0),
    ('multiple-reason-single-bit',5,1,0,1,1,12,10,0x08,0),
    ('failed-io-carries-reason',5,1,6,1,0,0,2,0,0),
    ('short-count-carries-ok',5,1,0,1,1,11,1,0,0),
    ('full-12B-carries-not-evaluated',5,1,0,1,1,12,0,0,0),
]:
    b=bytearray(raw);struct.pack_into('<BBB',b,213,r_byte,m_byte,res_byte)
    try:F.read0_header_record(bytes(b),op,point,status,returned,known,count)
    except R.Rejected:pass
    else:raise AssertionError(label+' accepted')

rows.append(dict(case='saved-frame-and-shape-header-forgeries-denied',status='PASS',variants=15,live_origin_recreated=False))
out=dict(status='FULL_CONTROLLER_V6_BOUNDED_HEADER_LOCALIZATION_PASS',checks=len(rows),rows=rows,
    native_helper_executed=False,actual_root_journal_modified=False,new_root_or_USB_operations=0,
    raw_header_or_HASP_or_auth_bytes_exported=False,whole_real_camera_flow_proven=False)
with (H/'header-localization-check.json').open('x')as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status=out['status'],groups=len(rows),new_root_or_USB_operations=0)))
