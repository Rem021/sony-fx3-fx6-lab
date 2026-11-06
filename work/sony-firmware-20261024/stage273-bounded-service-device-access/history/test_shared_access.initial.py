"""Exercise bounded policy through full ordinary-user helper/IPC fake flow."""
from pathlib import Path
import json,subprocess,sys
sys.dont_write_bytecode=True
import supervisor as S
import receipt_receiver as R
import controller_ipc as I
import flow_receiver as F
H=Path(__file__).resolve().parent
rows=[]
cases=[('shared-normal',131072|67108864,'HOST_RETURN_CONTROLLED_PORT_ASSOCIATION'),
       ('shared-control-only-denied',131072|33554432,'OWNER_RETAINED'),
       ('shared-interface-conflict',131072|65536,'OWNER_RETAINED')]
for name,option,expected in cases:
    d=H/'runs'/(name+'-seed');d.mkdir(mode=0o700);guard=d/'old.journal';spec=d/'recovery.bin'
    seed=subprocess.Popen([str(H/'artifacts/recovery-seed'),str(guard),str(spec),'0'],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    assert seed.stdout.readline()=='ready\n';seed.stdin.write('x');seed.stdin.flush();assert seed.wait(timeout=3)==0
    j=S.Job.fixture(name=name,fixture_option=option,guard=guard,recovery_spec=spec)
    try:
        result=j.wait(4);assert result['status']==expected,result
        a=j.flow_state.acquisition
        assert a['device_open_disposition']==2 and a['device_open_raw']==-536870203
        assert j.receipt['manual_recovery']['stage']==2 and not j.error
        if expected.startswith('HOST_RETURN'):
            assert result['helper_terminal_observed'] and result['bounded_service_read_observed']
            assert j.flow_state.complete and j.flow_state.body_bytes==88
            assert j.flow_state.calls[(0x0336,1)]==1 and j.flow_state.calls[(0x0336,7)]==1
            assert j.runner.wait(timeout=3)==0
        else:
            assert not result['bounded_service_read_observed'] and not j.flow_state.complete
            assert not any((0x0336,n)in j.flow_state.calls for n in [1,2,3,4,5,6,7,8,10])
            assert j.flow_state.pending is None
            assert a['step']==(206 if name=='shared-control-only-denied'else210)
        rows.append(dict(case=name,status='PASS',observed_status=result['status'],acquisition=a,
            real_helper_kernel_peer_and_private_receipt=True,device_driver_and_cache_are_artificial=True))
    finally:
        if j.runner.poll()is None:j.frame.fixture_gate(2);assert j.runner.wait(timeout=5)==90
        assert j.ipc.probe(j.verified.identity.pid)is None
        j.out.flush();j.err.flush()
        assert b'ERROR: AddressSanitizer'not in(j.directory/'relay-stdout.txt').read_bytes()
        assert b'runtime error:'not in(j.directory/'relay-stdout.txt').read_bytes()
        j.close_observer()

raw=bytearray(672);raw[:8]=b'FX3FLOW5'
import struct
struct.pack_into('<I',raw,592,203);struct.pack_into('<i',raw,596,-536870203)
struct.pack_into('<Ii',raw,600,2,-536870203)
assert F.acquisition_record(bytes(raw),11,1,8,1,-536870203)['device_open_disposition']==2
for label,offset,value in [('unknown-disposition',600,3),('owned-with-exclusive-error',600,1),('false-open-result',604,0)]:
    bad=bytearray(raw);struct.pack_into('<I',bad,offset,value)
    try:F.acquisition_record(bytes(bad),11,1,8,1,-536870203)
    except R.Rejected:pass
    else:raise AssertionError(label+' accepted')
rows.append(dict(case='device-open-capability-metadata-forgeries-denied',status='PASS',variants=3))
receipt=dict(status='BOUNDED_SHARED_SERVICE_FULL_FAKE_FLOW_PASS',rows=rows,native_helper_executed=False,
    actual_root_journal_modified=False,new_root_or_USB_operations=0,real_IOKit_or_camera_success_proven=False)
with(H/'shared-access-check.json').open('x')as f:json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status=receipt['status'],groups=len(rows),new_root_or_USB_operations=0)))
