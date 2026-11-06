"""New binding/scope/permit regression only. No live query, root or USB calls."""
from pathlib import Path
from hashlib import sha256
import copy,json,os,subprocess
import controller_ipc as I
import fixed_launch as P
import native_factory as N
import receipt_receiver as R
import supervisor as S
H=Path(__file__).resolve().parent;rows=[]
def deny(fn):
    try:fn()
    except (ValueError,R.Rejected):return
    raise AssertionError('invalid context accepted')
def authorized():
    return dict(authorization={P.AUTH_KEY:dict(authorized=True,grant_id=R.GRANT_ID,bundle_sha256=sha256((H/'approval-bundle.json').read_bytes()).hexdigest(),scope=P.SCOPE,
        maximum_helper_invocations=1,usb_capture_and_return=True,Sony_authentication_and_mode_transition=True,
        camera_fixed_read0_maximum_bytes=88,firmware_write=False,physical_port_registryID=json.loads((H/'fixed-material.json').read_text())['physical_port_registryID'],physical_custody_no_substitution_assumption=True)})
good=authorized();assert P.native_authority(good)['scope']==P.SCOPE
for key,value in [('authorized',1),('maximum_helper_invocations',True),('physical_custody_no_substitution_assumption',1),('physical_port_registryID',True),('scope','MSC_OWNER_STATUS_ONLY')]:
    g=copy.deepcopy(good);g['authorization'][P.AUTH_KEY][key]=value;deny(lambda:P.native_authority(g))
g=copy.deepcopy(good);g['authorization_consumption']={P.AUTH_KEY:dict(consumed=True)};deny(lambda:P.native_authority(g))
saved=N.preflight_query;called=[];N.preflight_query=lambda:called.append(True)
try:deny(lambda:N.prepare_native_session({}))
finally:N.preflight_query=saved
assert not called and not P.JOB.exists()
rows.append(dict(case='new_typed_scope_and_no_preapproval_query',status='PASS'))
material=json.loads((H/'fixed-material.json').read_text());target=material['target'];candidate=dict(target,physical_port_registryID=material['physical_port_registryID'])
observed=dict(candidate_count=1,candidates=[candidate],media_unknown=False,mounted_camera_media=[],storage_driver_classes=['IOUSBMassStorageDriver'],cached_media_BSD_names=[])
N.validate_preflight(observed,target)
for path,value in [('registryID',candidate['registryID']+1),('physical_port_registryID',candidate['physical_port_registryID']+1)]:
    x=copy.deepcopy(observed);x['candidates'][0][path]=value;deny(lambda:N.validate_preflight(x,target))
x=copy.deepcopy(observed);x['mounted_camera_media']=['disk10s1'];deny(lambda:N.validate_preflight(x,target))
rows.append(dict(case='fresh_target_physical_anchor_and_zero_media_gate',status='PASS'))
d=H/'runs/permit';d.mkdir(mode=0o700);p=d/'private';p.write_bytes((H/'permit.bin').read_bytes());p.chmod(0o400)
q=subprocess.run([I.build()['builds']['permit_test']['path'],str(H/'permit.bin'),str(p)],capture_output=True,text=True,timeout=4)
assert q.returncode==0 and 'AddressSanitizer'not in q.stderr and 'runtime error:'not in q.stderr,(q.returncode,q.stdout,q.stderr)
ipc=I.IPC();data,nonce=I.native_frame_bytes(ipc);g=I.Grant.from_buffer_copy(data,ipc.grant_offset)
assert len(data)==4096 and g.schema==6 and g.scope==0x53564334 and g.mode==0 and bytes(g.nonce)==nonce and not(g.fail or g.option or g.block)
rows.append(dict(case='physical_port_permit_and_native_frame_RAM_only',status='PASS',permit_checks=json.loads(q.stdout)))
j=S.Job.fixture(name='fresh-bound-no-service-serial',fixture_option=67108864)
try:
    result=j.wait(4);assert result['status']=='HOST_RETURN_CONTROLLED_PORT_ASSOCIATION',result
    assert j.flow_state.complete and j.flow_state.service_kind==2 and j.flow_state.witness_state==5
    j.runner.wait(timeout=3);assert j.ipc.probe(j.verified.identity.pid)is None
    assert(Path(j.expected_path).parent/'entry.once.flow').read_bytes()==b''.join(j.flow_frames)
    rows.append(dict(case='new_scope_complete_own_child',status='PASS',raw_frames=len(j.flow_frames),actual_camera=False))
finally:
    if j.runner.poll()is None:j.request_stop();j.frame.fixture_gate(2);j.runner.wait(timeout=5)
    j.out.flush();j.err.flush();raw=(j.directory/'runner-stderr.txt').read_bytes()+(j.directory/'relay-stdout.txt').read_bytes()
    assert b'ERROR: AddressSanitizer'not in raw and b'runtime error:'not in raw
    j.close_observer()
for x in json.loads((H/'approval-bundle.json').read_text())['files']:
    raw=(H/x['path']).read_bytes();assert len(raw)==x['bytes']and sha256(raw).hexdigest()==x['sha256'],x['path']
assert not P.JOB.exists()
rows.append(dict(case='fixed_members_and_no_native_staging',status='PASS'))
with(H/'package-test-receipt.json').open('x')as f:json.dump(dict(status='NEW_FIXED_PORT_PACKAGE_OFFLINE_PASS',checks=len(rows),rows=rows,actual_root_or_USB_commands=False,native_job_staged=False),f,indent=2);f.write('\n')
print(json.dumps(dict(status='PASS',checks=len(rows),actual_camera_trial=False)))
