"""Own C and IPC tests. USB, topology transitions and physical custody are artificial."""
from pathlib import Path
from hashlib import sha256
import copy,json,os,struct,subprocess
import cache_preflight as C
import flow_receiver as F
import receipt_receiver as R
import supervisor as S
H=Path(__file__).resolve().parent;rows=[]
cmd=['/usr/bin/xcrun','clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(H/'transition_identity.c'),str(H/'transition_unit.c'),'-o',str(H/'artifacts/transition-unit')]
q=subprocess.run(cmd,capture_output=True,text=True);assert q.returncode==0,q.stderr
q=subprocess.run([str(H/'artifacts/transition-unit')],capture_output=True,text=True,timeout=5)
assert q.returncode==0 and 'AddressSanitizer'not in q.stderr and 'runtime error:'not in q.stderr,(q.returncode,q.stdout,q.stderr)
rows.append(dict(case='bounded_identity_C_unit',status='PASS',compile_argv=cmd,stdout=q.stdout,binary_sha256=sha256((H/'artifacts/transition-unit').read_bytes()).hexdigest()))
cases=[('no-SERVICE-serial-SS',67108864,'HOST_RETURN_CONTROLLED_PORT_ASSOCIATION'),
       ('wrong-service-physical-port',268435456,'OWNER_RETAINED'),
       ('wrong-returned-serial',536870912,'OWNER_RETAINED'),
       ('unexpected-SERVICE-serial',1073741824,'OWNER_RETAINED'),
       ('control-only-no-SERVICE-serial',33554432,'HOST_CONTROL_RETURN_CAPABILITY_UNTESTED')]
for name,option,expected in cases:
    j=S.Job.fixture(name=name,fixture_option=option)
    try:
        value=j.wait(4);assert value['status']==expected,value
        assert j.flow_state.body_tag==b'A'*32
        if expected=='HOST_RETURN_CONTROLLED_PORT_ASSOCIATION':
            assert j.flow_state.complete and j.flow_state.service_kind==2 and j.flow_state.body_bytes==88
            assert j.flow_state.witness_state==5 and j.flow_state.return_node==300
            service_frames=[f for f in j.flow_frames if struct.unpack_from('<I',f,172)[0]>>16==0x0336]
            assert service_frames and all(f[176:208]==bytes(32)for f in service_frames)
        elif expected=='OWNER_RETAINED':
            assert not j.flow_state.complete and not j.flow_state.calls.get((0x0da1,9),0)
            if name!='wrong-returned-serial':assert not any(pid==0x0336 for pid,op in j.flow_state.calls)
        else:
            assert j.flow_state.complete and j.flow_state.control_only and j.flow_state.body_bytes==0
            assert not any(j.flow_state.calls.get((0x0336,k),0)for k in [1,2,3,4,5,6,7])
        rows.append(dict(case=name,status='PASS',observed_status=value['status'],flow_frames=len(j.flow_frames),physical_identity_artificial=True,global_camera_acceptance=False))
    finally:
        if j.runner.poll()is None:j.request_stop();j.frame.fixture_gate(2)
        j.runner.wait(timeout=5);assert j.ipc.probe(j.verified.identity.pid)is None
        j.out.flush();j.err.flush()
        raw=(j.directory/'runner-stderr.txt').read_bytes()+(j.directory/'relay-stdout.txt').read_bytes()
        assert b'ERROR: AddressSanitizer'not in raw and b'runtime error:'not in raw
        assert(Path(j.expected_path).parent/'entry.once.flow').read_bytes()==b''.join(j.flow_frames)
        j.close_observer()

# Parser-only attacks on saved own-fixture frames: no recreation of live origin.
d=H/'runs/no-SERVICE-serial-SS';identity=R.Identity(**json.loads((d/'verified-helper.json').read_text())['identity']);nonce=bytes.fromhex(json.loads((d/'spec.json').read_text())['nonce'])
frames=[p.read_bytes()for p in sorted(d.glob('flow-*.bin'))]
service_at=next(i for i,f in enumerate(frames)if struct.unpack_from('<I',f,172)[0]>>16==0x0336)
arm_at=next(i for i,f in enumerate(frames)if struct.unpack_from('<I',f,24)[0]==60)
for name,index,offset,replacement in [('copied-source-serial',service_at,176,b'A'*32),('changed-physical-anchor',service_at,448,struct.pack('<Q',999)),('missing-arm-marker',arm_at,24,struct.pack('<I',42))]:
    altered=[bytearray(f)for f in frames];altered[index][offset:offset+len(replacement)]=replacement;previous=bytes(32)
    for f in altered:f[608:640]=previous;f[640:]=sha256(f[:640]).digest();previous=f[640:]
    receiver=F.FlowReceiver(identity,nonce,R.GRANT_ID)
    try:
        for f in altered:receiver.accept(bytes(f))
    except R.Rejected:pass
    else:raise AssertionError(name+' accepted despite valid rebuilt hash chain')
rows.append(dict(case='saved_byte_forgery_rejected',status='PASS',variants=3,live_origin_recreated=False))
receipt=json.loads((H/'current-MSC-port-cache.json').read_text());anchor=json.loads(json.loads((H/'cached-port-probe-receipt.json').read_text())['stdout'])['physical_port_registryID']
target=receipt['target'];candidate=dict(target,physical_port_registryID=anchor)
observed=dict(candidate_count=1,candidates=[candidate],media_unknown=False,mounted_camera_media=[],storage_driver_classes=receipt['storage_driver_classes'],cached_media_BSD_names=[])
assert C.validate(observed,target,anchor)
for key,value in [('mounted_camera_media',['disk10s1']),('media_unknown',True),('storage_driver_classes',[])]:
    altered=copy.deepcopy(observed);altered[key]=value
    try:C.validate(altered,target,anchor)
    except ValueError:pass
    else:raise AssertionError('preflight failed to reject '+key)
rows.append(dict(case='ejected_zero_media_cache_preflight',status='PASS',zero_media_accepted=True,mounted_unknown_or_no_driver_rejected=True,no_new_query=True))
with(H/'transition-test-receipt.json').open('x')as f:
    json.dump(dict(status='CONTROLLED_PORT_ASSOCIATION_OWN_CODE_CHECKS_PASS',checks=len(rows),rows=rows,
        actual_root_or_USB_commands=False,actual_port_metadata_probe_is_a_separate_cache_receipt=True,
        no_camera_authentication_or_exit_proven=True),f,indent=2);f.write('\n')
print(json.dumps(dict(status='PASS',checks=len(rows),actual_camera_trial=False)))
