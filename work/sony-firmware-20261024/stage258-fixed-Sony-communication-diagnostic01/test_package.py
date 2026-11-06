"""Test only newly bound package/authority/native frame; no real backend."""
from pathlib import Path
from hashlib import sha256
from contextlib import contextmanager
import copy,json,os,subprocess
import controller_ipc as I
import fixed_launch as P
import native_factory as N
import receipt_receiver as R
import supervisor as S
H=Path(__file__).resolve().parent;rows=[]
def deny(fn):
    try:fn()
    except (R.Rejected,ValueError):return
    raise AssertionError('invalid context accepted')
def synthetic():
    return dict(authorization={P.AUTH_KEY:dict(authorized=True,grant_id=R.GRANT_ID,
        bundle_sha256=sha256((H/'approval-bundle.json').read_bytes()).hexdigest(),scope=P.SCOPE,
        maximum_helper_invocations=1,usb_capture_and_return=True,Sony_authentication_and_mode_transition=True,
        camera_fixed_read0_maximum_bytes=88,firmware_write=False)})
def boundaries():
    assert P.native_authority(synthetic())['scope']==P.SCOPE
    for field,value in [('authorized',1),('maximum_helper_invocations',True),('firmware_write',0),('Sony_authentication_and_mode_transition',1),('camera_fixed_read0_maximum_bytes',True),('scope','MSC_OWNER_STATUS_ONLY')]:
        x=synthetic();x['authorization'][P.AUTH_KEY][field]=value;deny(lambda:P.native_authority(x))
    x=synthetic();x['authorization_consumption']={P.AUTH_KEY:dict(consumed=True)};deny(lambda:P.native_authority(x))
    called=[];saved=N.preflight_query
    N.preflight_query=lambda:called.append(True)
    try:deny(lambda:N.prepare_native_session({}))
    finally:N.preflight_query=saved
    assert not called and not P.JOB.exists()
    target=json.loads((H/'fixed-material.json').read_text())['target']
    o=dict(candidate_count=1,candidates=[dict(target)],media_unknown=False,storage_driver_classes=['IOUSBMassStorageDriver'],cached_media_BSD_names=['disk99s1'],mounted_camera_media=[])
    N.validate_preflight(o,target)
    for key,value in [('mounted_camera_media',['disk99s1']),('media_unknown',True),('storage_driver_classes',[])]:
        x=copy.deepcopy(o);x[key]=value;deny(lambda:N.validate_preflight(x,target))
    x=copy.deepcopy(o);x['candidates'][0]['registryID']+=1;deny(lambda:N.validate_preflight(x,target))
    rows.append(dict(case='authority_and_preflight',status='PASS',live_queries=0,staging=False))
def permit_frame():
    d=H/'runs/permit';d.mkdir(mode=0o700);f=d/'good';f.write_bytes((H/'permit.bin').read_bytes());f.chmod(0o400)
    q=subprocess.run([I.build()['builds']['permit_test']['path'],str(H/'permit.bin'),str(f)],capture_output=True,text=True,timeout=3)
    assert q.returncode==0 and 'runtime error:' not in q.stderr and 'AddressSanitizer' not in q.stderr,(q.returncode,q.stdout,q.stderr)
    ipc=I.IPC();data,nonce=I.native_frame_bytes(ipc);g=I.Grant.from_buffer_copy(data,ipc.grant_offset)
    assert len(data)==4096 and g.mode==0 and g.uid==501 and g.scope==0x53564333 and g.schema==5
    assert bytes(g.nonce)==nonce and not(g.fail or g.option or g.block) and bytes(g.tag)==bytes(32)
    rows.append(dict(case='fixed_permit_and_native_frame_RAM_only',status='PASS',permit_checks=json.loads(q.stdout),frame_bytes=4096))
def child_case(name,option,expected):
    j=S.Job.fixture(name=name,fixture_option=option)
    try:
        value=j.wait(4);assert value['status']==expected,value
        assert j.flow_state.complete and j.receipt['transport_peer_verified']
        j.runner.wait(timeout=3)
        assert not I.IPC().probe(j.verified.identity.pid)
        assert (Path(j.expected_path).parent/'entry.once.flow').read_bytes()==b''.join(j.flow_frames)
        assert (j.directory/'received-final-record.bin').read_bytes()==(j.directory/'private-record.bin').read_bytes()
        rows.append(dict(case=name,status='PASS',observed_status=expected,frames=len(j.flow_frames),actual_root_or_USB=False))
    finally:
        if j.runner.poll() is None:
            j.request_stop();j.frame.fixture_gate(2);j.runner.wait(timeout=5)
        j.out.flush();j.err.flush()
        text=(j.directory/'runner-stderr.txt').read_bytes()
        if (j.directory/'relay-stdout.txt').exists():text+=(j.directory/'relay-stdout.txt').read_bytes()
        assert b'ERROR: AddressSanitizer' not in text and b'runtime error:' not in text
        j.close_observer()
def fixed_render():
    bundle=json.loads((H/'approval-bundle.json').read_text())
    for m in bundle['files']:
        raw=(H/m['path']).read_bytes();assert len(raw)==m['bytes'] and sha256(raw).hexdigest()==m['sha256'],m['path']
    plan=json.loads((H/'fixed-plan.json').read_text());command,body=P.render_native(plan['nonce'])
    assert sha256(command.encode()).hexdigest()==plan['terminal_command_sha256']
    assert subprocess.run(['/bin/sh','-n'],input=command,text=True,capture_output=True).returncode==0
    assert not P.JOB.exists()
    rows.append(dict(case='frozen_render_and_members',status='PASS',members=len(bundle['files']),command_executed=False))
if __name__=='__main__':
    boundaries();permit_frame()
    child_case('new-bound-match',0,'HOST_RETURN_CAMERA_STATE_UNVERIFIED')
    child_case('new-bound-mismatch',33554432,'HOST_CONTROL_RETURN_CAPABILITY_UNTESTED')
    fixed_render()
    with(H/'package-test-receipt.json').open('x')as f:json.dump(dict(status='NEW_PACKAGE_BOUNDARIES_AND_OWN_CHILD_PASS',checks=len(rows),rows=rows,actual_root_or_IOKit_executed=False,native_job_staged=False),f,indent=2);f.write('\n')
    print(json.dumps(dict(status='PASS',checks=len(rows),actual_root_or_IOKit_executed=False)))
