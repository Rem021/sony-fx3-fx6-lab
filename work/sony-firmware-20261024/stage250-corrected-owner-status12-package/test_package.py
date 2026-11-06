"""Own unprivileged tests of the new factory, permit and binding boundaries."""
from pathlib import Path
from contextlib import contextmanager
from hashlib import sha256
import json,os,struct,subprocess,copy,traceback
import controller_ipc as I
import fixed_launch as P
import native_factory as N
import supervisor as S
import receipt_receiver as R
H=Path(__file__).resolve().parent;rows=[]
def rejected(fn):
 try:fn()
 except (R.Rejected,ValueError):return
 raise AssertionError('invalid authority or target accepted')
def synthetic_goal():
 return {'authorization':{'Mac_owner_status12':{'authorized':True,'grant_id':R.GRANT_ID,
  'bundle_sha256':sha256((H/'approval-bundle.json').read_bytes()).hexdigest(),
  'scope':'MSC_OWNER_STATUS_ONLY','maximum_helper_invocations':1,
  'usb_capture_and_return':True,'sony_vendor_or_file_commands':False}}}
def permit_file_cases():
 d=H/'runs/permit-files';d.mkdir(mode=0o700)
 good=d/'good';good.write_bytes((H/'permit.bin').read_bytes());good.chmod(0o400)
 mode=d/'mode';mode.write_bytes(good.read_bytes());mode.chmod(0o600)
 link=d/'symbolic';link.symlink_to(good)
 hard=d/'hard';hard.write_bytes(good.read_bytes());hard.chmod(0o400);os.link(hard,d/'hard-second')
 short=d/'short';short.write_bytes(good.read_bytes()[:-1]);short.chmod(0o400)
 outcomes=[]
 for path,deny in [(good,False),(mode,True),(link,True),(hard,True),(short,True)]:
  env=os.environ.copy()
  if deny:env['EXPECT_PERMIT_FILE_DENY']='1'
  else:env.pop('EXPECT_PERMIT_FILE_DENY',None)
  args=[I.build()['builds']['permit_test']['path'],str(H/'permit.bin'),str(path)]
  q=subprocess.run(args,env=env,capture_output=True,text=True,timeout=3)
  assert q.returncode==0,(path.name,q.stderr,q.stdout,q.returncode)
  assert 'AddressSanitizer' not in q.stderr and 'runtime error:' not in q.stderr
  outcomes.append(dict(case=path.name,expected_deny=deny,checks=json.loads(q.stdout)))
 rows.append(dict(case='permit_file_and_registry_binding',status='PASS',file_cases=outcomes))

def native_frame():
 ipc=I.IPC();data,nonce=I.native_frame_bytes(ipc);g=I.Grant.from_buffer_copy(data,ipc.grant_offset)
 m=json.loads((H/'fixed-material.json').read_text())
 assert len(data)==4096 and g.mode==0 and g.uid==501 and bytes(g.nonce)==bytes.fromhex(m['nonce'])==nonce
 assert bytes(g.key)==bytes.fromhex(m['privacy_key']) and bytes(g.tag)==bytes(32) and bytes(g.observed)==bytes(32)
 assert not (g.fail or g.option or g.block) and g.observer==os.getpid()
 assert not P.JOB.exists()
 rows.append(dict(case='native_frame_encoding_without_staging',status='PASS',bytes=4096,job_created=False))

def authority_types():
 good=synthetic_goal();assert P.native_authority(good)['scope']=='MSC_OWNER_STATUS_ONLY'
 bad=[{}, {'authorization':{'Mac_root_host01':{'authorized':True}}}]
 for key,value in [('authorized',1),('maximum_helper_invocations',True),('maximum_helper_invocations',2),
                   ('usb_capture_and_return',1),('sony_vendor_or_file_commands',0),('scope','HOST_ONLY')]:
  d=copy.deepcopy(good);d['authorization']['Mac_owner_status12'][key]=value;bad.append(d)
 consumed=copy.deepcopy(good);consumed['authorization_consumption']={'Mac_owner_status12':{'consumed':True}};bad.append(consumed)
 for value in bad:rejected(lambda value=value:P.native_authority(value))
 assert not P.JOB.exists()
 rows.append(dict(case='exact_new_scope_and_typed_authority',status='PASS',rejections=len(bad),synthetic_values_only=True,canonical_authorization_written=False))

def unapproved_factory():
 current=json.loads((H.parent/'GOAL_STATUS.json').read_text());original=N.preflight_query;called=[]
 def forbidden():called.append(True);raise AssertionError('cache queried before approval')
 N.preflight_query=forbidden
 try:rejected(lambda:N.prepare_native_session(current))
 finally:N.preflight_query=original
 assert called==[] and not P.JOB.exists()
 rows.append(dict(case='unapproved_factory_stops_before_query_or_job',status='PASS',cache_queries=0,job_created=False))

def changed_target():
 m=json.loads((H/'fixed-material.json').read_text());actual=dict(m['target']);actual['registryID']+=1
 original=N.preflight_query;N.preflight_query=lambda:dict(candidate_count=1,candidates=[actual])
 try:rejected(lambda:N.prepare_native_session(synthetic_goal()))
 finally:N.preflight_query=original
 assert not P.JOB.exists()
 rows.append(dict(case='changed_registry_denied_before_job',status='PASS',synthetic_values_only=True,job_created=False))

@contextmanager
def job(**kw):
 j=S.Job.fixture(**kw)
 try:yield j
 finally:
  if j.runner.poll() is None:j.request_stop();j.frame.fixture_gate(2)
  j.runner.wait(timeout=5);j.out.flush();j.err.flush()
  text=(j.directory/'runner-stderr.txt').read_bytes()
  if (j.directory/'relay-stdout.txt').exists():text+=(j.directory/'relay-stdout.txt').read_bytes()
  assert b'ERROR: AddressSanitizer' not in text and b'runtime error:' not in text
  j.close_observer()

def owner_pipeline():
 with job() as j:
  value=j.wait(3);assert value['status']=='HOST_RETURN_OBSERVED',value
  assert len(j.responses)==3 and all(x['status']==0 for x in j.responses)
  assert j.receipt['transport_peer_verified'] and j.receipt['result']['vendor_attempted']==0
  events=[p for p,c in struct.iter_unpack('<Ii',j.receipt['result_bytes'][216:216+j.receipt['result']['event_count']*8])]
  assert [p for p in events if p>=100]==[102,103,104,105,106,107,108,109,109]
  assert (j.directory/'received-final-record.bin').read_bytes()==(j.directory/'private-record.bin').read_bytes()
  j.runner.wait(timeout=3)
  log=next(json.loads(x) for x in (j.directory/'relay-stdout.txt').read_text().splitlines() if x.startswith('{') and 'wire_calls' in x)
  assert log['wire_calls']==[0,0,0]
  rows.append(dict(case='new_supervisor_fixture_pipeline',status='PASS',wire_calls=log['wire_calls'],directory=str(j.directory.relative_to(H))))

def bad_hello():
 with job() as j:
  orig=j._hello
  def corrupt(data):
   changed=bytearray(data);changed[88]^=1;changed[128:]=sha256(changed[:128]).digest();orig(bytes(changed))
  j._hello=corrupt;value=j.wait(3)
  assert value['status']=='UNKNOWN_OBSERVER_ERROR' and not j.receiver.acknowledged and not j.guard.exists(),value
  rows.append(dict(case='wrong_image_still_denied_before_owner',status='PASS',directory=str(j.directory.relative_to(H))))

def bundle_and_command():
 raw=(H/'approval-bundle.json').read_bytes();bundle=json.loads(raw)
 for x in bundle['files']:
  data=(H/x['path']).read_bytes();assert len(data)==x['bytes'] and sha256(data).hexdigest()==x['sha256']
 plan=json.loads((H/'fixed-plan.json').read_text());command,body=P.render_native(plan['nonce'])
 assert sha256(command.encode()).hexdigest()==plan['terminal_command_sha256']
 assert 'install -m 400' in body and '/permit.bin' in body and 'sudo -- ' in command
 assert subprocess.run(['/bin/sh','-n'],input=command,text=True,capture_output=True,timeout=2).returncode==0
 assert not P.JOB.exists()
 rows.append(dict(case='frozen_package_and_permit_command_syntax',status='PASS',files=len(bundle['files']),bundle_sha256=sha256(raw).hexdigest(),command_executed=False))

for fn in (permit_file_cases,native_frame,authority_types,unapproved_factory,changed_target,owner_pipeline,bad_hello,bundle_and_command):
 try:fn()
 except Exception as exc:
  with (H/'package-test-failure.json').open('x') as f:json.dump(dict(case=fn.__name__,error=repr(exc),traceback=traceback.format_exc(),passed=rows),f,indent=2)
  raise
 print(rows[-1]['case']+': PASS',flush=True)
with (H/'package-test-receipt.json').open('x') as f:
 json.dump(dict(status='OWN_CODE_FIXED_STATUS_PACKAGE_OFFLINE_CHECKS_PASS',checks=len(rows),rows=rows,
  new_root_helper_or_USB_operations=0,live_cache_queries=0,native_job_staged=False,native_helper_executed=False,
  not_integrated_root_or_camera_acceptance=True),f,indent=2);f.write('\n')
