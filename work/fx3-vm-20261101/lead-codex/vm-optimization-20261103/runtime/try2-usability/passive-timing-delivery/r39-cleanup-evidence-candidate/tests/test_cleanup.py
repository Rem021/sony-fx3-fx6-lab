"""Real files/CLI/locks; all native, browser, PID and port responses explicitly mock."""
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys,time,uuid,fcntl
O=Path(__file__).resolve().parents[1];results=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def make(name):
 here=O/'run-inputs'/('fixture-f02ee53c27b9-'+name+'-'+uuid.uuid4().hex[:8]);a=[sys.executable,'-B',str(O/'prepare_run.py'),'--run-dir',str(here),'--task-id','task_f02ee53c27b9','--dispatch-id','ctx_0891bdba0ed8','--session','fx3-deadline-r39-fixture-'+name]
 p=subprocess.run(a,capture_output=True);assert p.returncode==0,p.stderr
 for ext,b in [('stdout',p.stdout),('stderr',p.stderr)]:(O/'receipts'/('prepare-'+here.name+'.'+ext)).write_bytes(b)
 native=here/'native-runs'/('v35diag-n64-r36-r39-'+uuid.uuid4().hex[:8]);native.mkdir(parents=True)
 c={'url':'http://127.0.0.1:54321/','run':str(native),'runner_pid':52001,'launch_id':str(uuid.uuid4())};put(here/'runtime.json',c)
 locks=[]
 for n in (1,2):p=here/('platform-lock-'+str(n));p.write_text('fixture lock');locks.append({'path':str(p),'free_at_close':True})
 profile='r35-diagnostic-r36-n64-r39';candidate=O.parent/'r36-fixed-slot-package/candidate.json';candidate_sha='0bf214178ab8e60d1ac7755e1d1b2fcc0d2c325ff8473abd50402f09ab81fab4'
 put(here/'RUNNER-LAUNCH.json',{'pid':52001,'argv':['python3','-B',str(O/'run_trial_r24_review_snapshot.py'),'--port','0','--max-minutes','8','--max-steps','32','--snapshot-tail','--gate-publish-interval','64','--pre-input-snapshot-step','2','--r35-diagnostic-package']})
 put(native/'command.json',{'args':['fixture-qemu-executable'],'cwd':str(native),'candidate':str(candidate),'candidate_sha256':candidate_sha,'r35_diagnostic_selection':{'profile':profile}})
 put(native/'trial-session.json',{'run':str(native),'url':c['url'].rstrip('/'),'observer_pid':52001,'qemu_pid':52002,'host_launch_uuid':'fixture-host-launch'})
 put(native/'receipt.json',{'run':str(native),'candidate':str(candidate),'candidate_sha256':candidate_sha,'qemu_pid':52002,'qemu_exit':0,'process_reaped':True,'PID_absent':True,'locks':locks,'cleanup':{'API16_restored':True,'quit_sent':True},'observer_source_snapshot':[{'name':n,'sha256':sha(O/n)} for n in ('run_trial_r24_review_snapshot.py','r35_package_selection.py','trial_web_r24_review_snapshot.py','startup_observation.py')]})
 put(native/'trial-web-final-receipt.json',{'acknowledged':True,'end_reason':'browser_ack','maximum_wait_seconds':30,'scope':'browser_receipt_delivery_only'})
 put(native/'resource-guard-receipt.json',{'process_reaped':True,'locks_released_after_reap':True,'events':[{'event':'process_reaped','pid':52002}]})
 return here

def invoke(here,scenario='success',mode='cleanup',wait=True):
 a=[sys.executable,'-B',str(O/'tests/fixture_cli.py'),scenario,mode];env={**os.environ,'FX3_NAV_RUN_DIR':str(here),'PYTHONDONTWRITEBYTECODE':'1'}
 if not wait:return subprocess.Popen(a,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
 p=subprocess.run(a,capture_output=True,env=env,timeout=20);prefix=O/'receipts'/('call-'+here.name+'-'+scenario+'-'+uuid.uuid4().hex[:8])
 Path(str(prefix)+'.stdout').write_bytes(p.stdout);Path(str(prefix)+'.stderr').write_bytes(p.stderr)
 if mode=='cleanup' and p.stdout:
  try:v=json.loads(p.stdout)
  except Exception:raise AssertionError((p.returncode,p.stdout,p.stderr))
 else:v={}
 return p,v

def counts(here):
 r=[]
 for p in here.glob('mock-calls-*.json'):r.extend(json.loads(p.read_text()))
 return {k:sum(x['kind']==k for x in r) for k in ('browser','End','HAR','close','deadline','failure_dispatch_once')}
def snapshot(call):return {str(p.relative_to(call)):sha(p) for p in call.rglob('*') if p.is_file()}
def result(name,here,**kw):results.append({'test':name,'run_dir':str(here),'mock_counts':counts(here),**kw})
def good(here):
 p,v=invoke(here);assert p.returncode==0 and v['status']=='completed',(v,p.stderr);return v
h=make('repeat');first=good(h);call=Path(first['receipt_path']).parent;before=snapshot(call);before_counts=counts(h);p,second=invoke(h)
assert p.returncode==0 and second['status']=='already-cleaned',(second,p.stderr)
assert counts(h)==before_counts and snapshot(call)==before
index=json.loads((h/'CLEANUP.json').read_text());assert index['first_invocation']['call_id']==first['call_id'] and index['completed_invocation']['call_id']==first['call_id'] and index['latest_invocation']['call_id']==second['call_id']
# Audit consumes original validated completion even though latest is already-cleaned.
p,_=invoke(h,'success','audit');assert p.returncode==0,p.stderr
result('success_repeat_and_actual_audit',h,first=first['receipt_reference'],second=second['receipt_reference'],first_bytes_unchanged=True)

for case in ['end-fail','transport','stage-write-fail','invocation-write-fail','exclusive-stage-collision','armed','malformed-alarm','result-write-fail','index-write-fail']:
 h=make(case);p,v=invoke(h,case);assert p.returncode!=0 and v['status']=='unknown',(case,v,p.stderr)
 assert counts(h)['End']==1 and counts(h)['close']==1,(case,counts(h))
 assert not (h/'CLEANUP-COMPLETED.json').exists()
 prior={p.name:snapshot(p) for p in (h/'cleanup-calls').iterdir()}
 second=good(h);assert counts(h)['End']==2
 for name,hashes in prior.items():assert snapshot(h/'cleanup-calls'/name)==hashes
 if case=='exclusive-stage-collision':
  assert (h/'cleanup-calls'/next(iter(prior))/'End-original-button-process.json').read_bytes()==b'fixture original sentinel'
 if case in ('armed','malformed-alarm'):
  calls=[x for p in h.glob('mock-calls-*.json') for x in json.loads(p.read_text())]
  assert sum(x['kind']=='deadline' and x['action']=='dispose' for x in calls)==1 # only the second safe call
 if case=='transport':
  p=h/'cleanup-calls'/next(iter(prior))/'End-original-button-stdout.txt';assert p.read_text()=='partial stdout'
 result('partial_'+case+'_then_explicit_cleanup',h,original_unknown=True,retry_is_new_explicit_cleanup_not_input=True)

# Invalid/old proof never becomes already-cleaned and never operates a browser.
for case in ['missing-result','corrupt-result','corrupt-manifest','missing-ACK','corrupt-PNG','corrupt-public-stdout','wrong-run-ref','wrong-source-ref','wrong-session','wrong-launch','wrong-run','native-changed','resource-fail','runner-live','qemu-live','port-live','port-fail','lock-held']:
 h=make(case);first=good(h);original_counts=counts(h);call=Path(first['receipt_path']).parent;ref=json.loads((h/'CLEANUP-COMPLETED.json').read_text());lock=None
 if case=='missing-result':(call/'result.json').unlink()
 elif case=='corrupt-result':(call/'result.json').write_text('{}')
 elif case=='corrupt-manifest':(call/'MANIFEST.json').write_text('{}')
 elif case=='missing-ACK':(call/'native/trial-web-final-receipt.json').unlink()
 elif case=='corrupt-PNG':(call/'ended-page.png').write_bytes(b'bad')
 elif case=='corrupt-public-stdout':(call/'return.stdout.txt').write_text('{}')
 elif case=='wrong-run-ref':ref['receipt_path']=str(h/'other/result.json');put(h/'CLEANUP-COMPLETED.json',ref)
 elif case=='wrong-source-ref':
  v=json.loads((call/'result.json').read_text());v['binding']['source_root']='old-source';put(call/'result.json',v)
  # Rehash to test semantic identity, beyond a simple damaged hash.
  m=json.loads((call/'MANIFEST.json').read_text());m['files']['result.json']={'sha256':sha(call/'result.json'),'bytes':(call/'result.json').stat().st_size};put(call/'MANIFEST.json',m)
  ref.update(receipt_sha256=sha(call/'result.json'),manifest_sha256=sha(call/'MANIFEST.json'));put(h/'CLEANUP-COMPLETED.json',ref)
 elif case=='wrong-session':
  cfg=json.loads((h/'config.json').read_text());cfg['session']+='-later';put(h/'config.json',cfg)
 elif case in ('wrong-launch','wrong-run'):
  c=json.loads((h/'runtime.json').read_text());c['launch_id']=str(uuid.uuid4()) if case=='wrong-launch' else c['launch_id']
  if case=='wrong-run':c['run']=str(h/'native-runs/v35diag-n64-r36-r39-other')
  put(h/'runtime.json',c)
 elif case=='native-changed':
  c=json.loads((h/'runtime.json').read_text());p=Path(c['run'])/'trial-web-final-receipt.json';v=json.loads(p.read_text());v['acknowledged']=False;put(p,v)
 elif case=='lock-held':lock=(h/'platform-lock-1').open('rb');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 scenario=case if case in ('resource-fail','runner-live','qemu-live','port-live','port-fail') else 'success'
 p,v=invoke(h,scenario)
 if lock:lock.close()
 assert p.returncode!=0 and v['status']=='unknown' and counts(h)==original_counts,(case,v,p.stderr,counts(h),original_counts)
 result('reject_'+case,h,status=v['status'],reason=v['errors'])

h=make('concurrent');owner=invoke(h,'owner',wait=False);limit=time.monotonic()+5
while not (h/'owner-entered').exists() and time.monotonic()<limit:time.sleep(.01)
assert (h/'owner-entered').exists();inode=(h/'.cleanup-owner.lock').stat().st_ino;t=time.monotonic();p,busy=invoke(h);elapsed=time.monotonic()-t
assert p.returncode!=0 and busy['status']=='busy' and elapsed<3,(busy,p.stderr,elapsed)
assert counts(h)['End']==1 and counts(h)['HAR']==0
(h/'release-owner').write_text('continue');out,err=owner.communicate(timeout=10);assert owner.returncode==0,(out,err)
(O/'receipts/concurrent-owner.stdout').write_bytes(out);(O/'receipts/concurrent-owner.stderr').write_bytes(err)
assert json.loads(out)['status']=='completed' and (h/'.cleanup-owner.lock').stat().st_ino==inode
result('concurrent_single_real_flock_owner',h,busy_seconds=elapsed,owner_exit=owner.returncode)

h=make('interrupted');p,_=invoke(h,'interrupt');assert p.returncode==93 and not (h/'CLEANUP-COMPLETED.json').exists();inode=(h/'.cleanup-owner.lock').stat().st_ino;prior={p.name:snapshot(p) for p in (h/'cleanup-calls').iterdir()};good(h)
assert counts(h)['End']==2 and (h/'.cleanup-owner.lock').stat().st_ino==inode
for name,hashes in prior.items():assert snapshot(h/'cleanup-calls'/name)==hashes
result('owner_process_exit_releases_fd_same_inode',h)

h=make('operate-failure');p,v=invoke(h,'success','operate-fail');assert p.returncode==19,(p.returncode,p.stdout,p.stderr)
assert json.loads((h/'FAILURE.json').read_text())['action']=='pin';assert counts(h)['failure_dispatch_once']==1
raw=list((h/'cleanup-dispatches').glob('*/dispatch.json'));assert len(raw)==1
v=json.loads(raw[0].read_text());assert v['returncode']==0 and v['status']=='completed' and v['original_action_failed']
before={str(p):sha(p) for p in (h/'cleanup-calls').rglob('*') if p.is_file()};_,v=invoke(h);assert v['status']=='already-cleaned'
assert all(sha(Path(p))==digest for p,digest in before.items());result('actual_operate_guard_dispatch_preserves_original_failure',h,operate_exit=19)
h=make('prelaunch');c=json.loads((h/'runtime.json').read_text());c['launch_id']=None;put(h/'runtime.json',c)
p,v=invoke(h);assert p.returncode!=0 and v['status']=='unknown' and counts(h)['End']==1 and counts(h)['close']==1 and not (h/'CLEANUP-COMPLETED.json').exists()
result('prelaunch_still_End_close_no_completion_certificate',h)
h=make('symlink-owner');(h/'lock-target').write_text('fixture only');(h/'.cleanup-owner.lock').symlink_to(h/'lock-target');p,v=invoke(h)
assert p.returncode!=0 and v['status']=='unknown' and counts(h)['End']==0
result('symlink_lock_unknown_no_unowned_action',h)
# Coordinator msg_65bdcb794e26: a damaged/cross-run completion index cannot
# prevent End on an independently verified current live run. Final native
# evidence appears only when the mock original End is executed.
for case in ('broken-index-live','cross-index-live','wrong-current-owner','wrong-current-page'):
 h=make(case);native=Path(json.loads((h/'runtime.json').read_text())['run']);pending=h/'pending-native';pending.mkdir()
 for name in ('receipt.json','trial-web-final-receipt.json','resource-guard-receipt.json'):(native/name).rename(pending/name)
 bad=b'{broken completion index'
 prior_snapshot=None;old_call=None
 if case=='cross-index-live':
  old=make('old-completion-source');old_value=good(old);old_call=Path(old_value['receipt_path']).parent;prior_snapshot=snapshot(old_call);bad=(old/'CLEANUP-COMPLETED.json').read_bytes()
 (h/'CLEANUP-COMPLETED.json').write_bytes(bad)
 p,v=invoke(h,case)
 if case in ('broken-index-live','cross-index-live'):
  assert p.returncode==0 and v['status']=='completed' and counts(h)['End']==1,(case,v,p.stderr)
  archived=Path(v['superseded_invalid_completion']['path']);assert archived.read_bytes()==bad
  if old_call:assert snapshot(old_call)==prior_snapshot
  current_counts=counts(h);p,v2=invoke(h);assert p.returncode==0 and v2['status']=='already-cleaned' and counts(h)==current_counts
  result('invalid_index_live_owned_End_then_preserved_'+case,h,archived_sha256=sha(archived),current_cleanup_completed=True)
 else:
  assert p.returncode!=0 and v['status']=='unknown' and v['End_required'] and counts(h)['End']==0,(case,v,p.stderr)
  assert counts(h)['browser']==(1 if case=='wrong-current-page' else 0)
  result('invalid_index_without_current_ownership_'+case,h,End_required=True)
for case in ('bad-native-ACK','bad-native-reap','bad-native-source'):
 h=make(case);native=Path(json.loads((h/'runtime.json').read_text())['run'])
 if case=='bad-native-ACK':
  p=native/'trial-web-final-receipt.json';v=json.loads(p.read_text());v['acknowledged']=False
 else:
  p=native/'receipt.json';v=json.loads(p.read_text())
  if case=='bad-native-reap':v['process_reaped']=False
  else:v['observer_source_snapshot'][0]['sha256']='0'*64
 put(p,v);p,v=invoke(h);assert p.returncode!=0 and v['status']=='unknown' and counts(h)['End']==1 and counts(h)['close']==1 and not (h/'CLEANUP-COMPLETED.json').exists()
 result('first_cleanup_cannot_certify_'+case,h)
put(O/'CLEANUP-TESTS.json',{'fixture_only':True,'native_visual_process_port':'mock','files_flock':'real APFS test directories only','cases':results,'passed':True})
print('PASS',len(results),'cleanup cases; no real browser/process/port/QMP/guest')
