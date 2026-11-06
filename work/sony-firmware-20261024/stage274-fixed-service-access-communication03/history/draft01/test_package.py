"""New binding and authority checks; no native helper, Terminal or device call."""
from pathlib import Path
from hashlib import sha256
import ast,copy,ctypes,json,os,struct,subprocess
import controller_ipc as I
import fixed_launch as P
import native_factory as N
import receipt_receiver as R
import supervisor as S
H=Path(__file__).resolve().parent
assert os.getuid()==os.geteuid()==501 and not P.JOB.exists()
bundle_bytes=(H/'approval-bundle.json').read_bytes();bundle=json.loads(bundle_bytes)
digest=sha256(bundle_bytes).hexdigest();material=json.loads((H/'fixed-material.json').read_text())
rows=[]
def passed(name,**more):rows.append(dict(case=name,status='PASS',**more))
def denied(fn):
    try:fn()
    except R.Rejected:return
    raise AssertionError('expected fail-closed rejection')

expected=P.authorization_expectation(bundle,digest)
valid=dict(authorization={P.AUTH_KEY:expected})
assert P.native_authority(valid)==bundle
for key,value in [
    ('authorized',1),('scope','MSC_SERVICE_AUTH_READ0_CONTROLLED_PORT_RETURN'),
    ('host_manual_recovery_journal_append',False),('preserve_old_journal',False),
    ('global_guard_path','/private/tmp/different.journal'),('maximum_helper_invocations',True),
    ('firmware_write',0),('bundle_sha256','0'*64),('camera_fixed_read0_maximum_bytes',89),
    ('bounded_device_exclusive_conflict_fallback',False),('SERVICE_interface_must_be_owned',False),
    ('shared_control_only_STOP_forbidden',False),('default_pipe_background_concurrency_unproven',False)]:
    bad=copy.deepcopy(valid);bad['authorization'][P.AUTH_KEY][key]=value
    denied(lambda:P.native_authority(bad))
bad=copy.deepcopy(valid);bad['authorization'][P.AUTH_KEY]['extra']=True
denied(lambda:P.native_authority(bad))
bad=copy.deepcopy(valid);bad['authorization']['Mac_manual_recovery_communication02']=bad['authorization'].pop(P.AUTH_KEY)
denied(lambda:P.native_authority(bad))
bad=copy.deepcopy(valid);bad['authorization_consumption']={P.AUTH_KEY:dict(consumed=True)}
denied(lambda:P.native_authority(bad))
passed('new-exact-authority-and-consumption',negative_variants=16,fake_authority_only=True)

called=[];original=N.preflight_query
N.preflight_query=lambda:called.append(True)
try:denied(lambda:N.prepare_native_session({}))
finally:N.preflight_query=original
assert not called and not P.JOB.exists()
passed('unauthorized-factory-denies-before-query-or-staging')

target=material['target'];physical=material['physical_port_registryID']
observed=dict(candidate_count=1,candidates=[dict(target,physical_port_registryID=physical)],
    cached_media_BSD_names=[],storage_driver_classes=['IOUSBMassStorageInterfaceNub'],
    mounted_camera_media=[],media_unknown=False)
N.validate_preflight(observed,target)
for key in ['registryID','locationID','PID','physical_port_registryID']:
    bad=copy.deepcopy(observed);bad['candidates'][0][key]+=1
    denied(lambda:N.validate_preflight(bad,target))
for key,value in [('mounted_camera_media',['disk999s1']),('media_unknown',True),
                  ('storage_driver_classes',[]),('candidate_count',2)]:
    bad=copy.deepcopy(observed);bad[key]=value
    denied(lambda:N.validate_preflight(bad,target))
passed('fixed-target-port-and-ejected-volume-gate',negative_variants=8,known_zero_media_allowed=True)

job=S.Job();N.configure_manual_observation(job,material)
assert job.require_manual_recovery is True
assert job.recovery_expected==dict(source_node=target['registryID'],physical_port=physical,location=target['locationID'])
tree=ast.parse((H/'native_factory.py').read_text())
factory=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='prepare_native_session')
assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='configure_manual_observation' for n in ast.walk(factory))
passed('native-factory-explicit-manual-recovery-observation')

permit=(H/'permit.bin').read_bytes()
assert len(permit)==96 and permit[:16]==b'FX3SHAREPERMIT1\0'
assert struct.unpack_from('<II',permit,16)==(3,0x53564338)
assert struct.unpack_from('<IIQQ',permit,40)==(target['locationID'],7,target['registryID'],physical)
assert permit[64:]==sha256(permit[:64]).digest()
d=H/'runs/package-binding-check';d.mkdir(mode=0o700)
f=d/'permit.bin';f.write_bytes(permit);os.chmod(f,0o400)
p=subprocess.run([I.build()['builds']['permit_test']['path'],str(H/'permit.bin'),str(f)],capture_output=True,text=True)
assert p.returncode==0,(p.returncode,p.stderr)
permit_checks=json.loads(p.stdout)['permit_and_registry_checks'];assert permit_checks==17
passed('new-permit-version-scope-flags-target-and-file',checks=permit_checks)

ipc=I.IPC();raw,_=I.native_frame_bytes(ipc)
frame=I.Grant.from_buffer_copy(raw,ipc.grant_offset)
assert frame.schema==10 and frame.scope==0x53564338 and frame.mode==0
assert frame.fail==frame.option==frame.block==frame.claimed==frame.started==0
assert not P.JOB.exists()
passed('native-shared-frame-new-scope-own-RAM-only')

prior=json.loads((H/'fixed-prior-evidence.json').read_text());root=H.parents[2]
for m in prior['files']:assert sha256((H/m['path']).read_bytes()).hexdigest()==m['sha256']
for m in bundle['files']:
    p=H/m['path'];assert p.is_relative_to(H) and p.stat().st_size==m['bytes']
    assert sha256(p.read_bytes()).hexdigest()==m['sha256']
plan=json.loads((H/'fixed-plan.json').read_text())
assert plan['maximum_transition_window_ms']==5000 and plan['maximum_samples_per_transition']==50
assert plan['host_manual_recovery_journal_append'] and plan['preserve_old_journal']
assert plan['global_guard']==str(P.ROOT_BASE/'global-fx3-owner.journal')
command,body=P.render_native(material['nonce'])
assert command.encode()==(H/'SonyCommunication.command.txt').read_bytes()
assert body.encode()==(H/'root-body-render-only.sh.txt').read_bytes()
assert sha256(command.encode()).hexdigest()==plan['terminal_command_sha256']
passed('all-fixed-members-prior-evidence-and-rendered-command',members=len(bundle['files']))

result=dict(status='FIXED_MANUAL_RECOVERED_COMMUNICATION_PACKAGE_OFFLINE_PASS',checks=len(rows),rows=rows,
    approval_bundle_sha256=digest,native_helper_executed=False,actual_root_journal_modified=False,
    actual_job_created=False,root_or_USB_requests=0,new_camera_trial_authorized=False)
with (H/'package-test-receipt.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
