import hashlib,json,subprocess,sys,time,urllib.request,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence';OUT.mkdir(exist_ok=True)
SESSION='fx3-r19-'+uuid.uuid4().hex[:8];OUT=OUT/SESSION;OUT.mkdir();RESULT={'scope':'offline Chrome + actual PAGE/TrialState; no VM','cases':{}}
def browser(*args,stdin=None):
 p=subprocess.run(['agent-browser','--session',SESSION,*args],input=stdin,text=True,capture_output=True,timeout=30)
 if p.returncode:raise RuntimeError((p.stdout+p.stderr)[:1000])
 return p.stdout.strip()
def ev(js):return json.loads(browser('eval','--stdin',stdin=js))
def control(url,path,data={}):
 req=urllib.request.Request(url+'/'+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=4) as f:return json.load(f)
def stats(u):
 with urllib.request.urlopen(u+'/stats',timeout=4) as f:return json.load(f)
def page():return ev('({displayed,shownSHA,displayedGeneration,ready:lastStatus?.ready,phase:lastStatus?.phase,statusSHA:lastStatus?.frame?.PNG_sha256,statusGeneration:lastStatus?.frame?.content_generation,disabled:document.querySelector(\'[data-key="427"]\').disabled,summary:document.querySelector("#failure-summary").textContent,busy,ending,deliveryUnknown,held:!!window.__resumePreflight,confirmDisabled:document.querySelector("#confirm").disabled,startDisabled:document.querySelector("#start").disabled})')
def wait(fn,t=4):
 end=time.monotonic()+t
 while time.monotonic()<end:
  v=page()
  if fn(v):return v
  time.sleep(.04)
 raise AssertionError('wait '+repr(v))
def record(name,u):
 p=OUT/(name+'.png');browser('screenshot',str(p));RESULT['cases'][name]={'page':page(),'server':stats(u),'screenshot':p.name,'screenshot_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def reset(u):
 control(u,'reset');browser('open',web);wait(lambda v:v['displayed']==1 and not v['disabled'])
def hold():
 ev('''(() => {const orig=window.fetch.bind(window);window.__holdOn=true;window.__resumePreflight=null;window.fetch=(url,opt)=>{if(window.__holdOn && busy && String(url).includes('/api/status')){window.__holdOn=false;return new Promise(resolve=>{window.__resumePreflight=()=>resolve(orig(url,opt));});}return orig(url,opt);};return true})()''')
def click():ev('(() => {document.querySelector(\'[data-key="427"]\').click();return true})()')
def release():ev('(() => {if(!window.__resumePreflight) return false;window.__resumePreflight();window.__resumePreflight=null;return true})()')
LAUNCH='11111111-1111-4111-8111-111111111111'
NONCE='22222222-2222-4222-8222-222222222222'
def alarm():
 js="""(() => {const n=%s,l=%s;const armed=performance.now();
 window.__alarmState={nonce:n,state:'armed',armed_ms:armed,due_ms:armed+20000};
 Object.defineProperty(window,'__fx3InteractionDeadlineV1',{value:{status:()=>({version:1,sealed:false,deadline_ms:20000,
 expectedURL:location.href,expectedLaunchId:l,documentTimeOrigin:performance.timeOrigin,current:{...window.__alarmState}})}});
 return true})()"""%(json.dumps(NONCE),json.dumps(LAUNCH))
 ev(js)
def attempt():return ev('fx3KeyAttemptOutcome()')
def eligible(changes=None):
 a=attempt();assert a
 b=dict(attempt_id=a['attempt_id'],document_time_origin=a['document_time_origin'],launch_request_id=a['launch_request_id'],key=a['key'],base_step=a['base_step'],expected_step=a['expected_step'],PNG_sha256=a['frame']['PNG_sha256'],content_generation=a['frame']['content_generation'],sequence=a['frame']['sequence'],nonce=a['alarm_nonce'])
 b.update(changes or {})
 return ev('fx3KeyAttemptRecoveryEligibility('+json.dumps(b)+')')
ready=OUT/'fixture-ready.json';ready.unlink(missing_ok=True)
proc=subprocess.Popen([sys.executable,'-u',str(ROOT/'tests/race_harness.py'),'--module',str(ROOT/'trial_web_v22_navigation_review.py'),'--ready-file',str(ready)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
try:
 until=time.monotonic()+5
 while not ready.exists() and time.monotonic()<until:time.sleep(.03)
 assert ready.exists();urls=json.loads(ready.read_text());web=urls['web'];u=urls['control']
 reset(u);alarm();click();wait(lambda v:attempt()['outcome']=='accepted');RESULT['cases']['accepted_not_recoverable']={'attempt':attempt(),'eligibility':eligible(),'stats':stats(u)}
 assert not eligible()['eligible'] and stats(u)['enqueued']==1
 reset(u);alarm();hold();click();wait(lambda v:v['held']);control(u,'publish',{'color':'B'});wait(lambda v:v['displayedGeneration']==2 and v['held']);release();wait(lambda v:attempt()['outcome']=='not_posted' and not v['disabled']);record('local-no-post',u)
 x=eligible();assert x['eligible'] and not x['server_atomic_permission'] and stats(u)['requests']['key']==0
 assert not eligible({'nonce':'33333333-3333-4333-8333-333333333333'})['eligible']
 assert not eligible({'document_time_origin':0})['eligible']
 assert not eligible({'attempt_id':'33333333-3333-4333-8333-333333333333'})['eligible']
 RESULT['cases']['local_recovery_bindings']={'valid':x,'wrong_nonce':eligible({'nonce':'33333333-3333-4333-8333-333333333333'}),'wrong_document':eligible({'document_time_origin':0})}
 ev('(() => {window.__alarmState.due_ms=performance.now()-1;return true})()');assert not eligible()['eligible']
 ev('(() => {delete window.__alarmState.due_ms;return true})()');assert not eligible()['eligible']
 ev('(() => {window.__alarmState.due_ms=Infinity;return true})()');assert not eligible()['eligible']
 reset(u);alarm();control(u,'mode',{'mode':'stale_sha'});click();wait(lambda v:attempt()['outcome']=='explicit_rejected_unqueued' and not v['disabled']);record('matched-409-unqueued',u)
 assert eligible()['eligible'] and stats(u)['enqueued']==0
 old=attempt();control(u,'mode',{'mode':'delayed_accept'});click();wait(lambda v:attempt()['outcome']=='post_in_flight')
 assert attempt()['attempt_id']!=old['attempt_id'] and not eligible()['eligible'] and '本次按键未被接收' in page()['summary']
 wait(lambda v:attempt()['outcome']=='accepted');record('new-B-accepted-old-rejection-not-recovery',u)
 assert not eligible()['eligible'] and stats(u)['enqueued']==1
 reset(u);alarm();control(u,'mode',{'mode':'delayed_structured_409'});click();wait(lambda v:attempt()['outcome']=='post_in_flight');assert not eligible()['eligible'];wait(lambda v:attempt()['outcome']=='explicit_rejected_unqueued');record('inflight-then-matched-409',u)
 for mode in ('http500','invalid_json','wrong_request_id_409','timeout'):
  reset(u);alarm();control(u,'mode',{'mode':mode});click();wait(lambda v:attempt()['outcome']=='delivery_unknown',t=11);assert not eligible()['eligible'];record(mode+'-unknown',u)
 reset(u);alarm();control(u,'mode',{'mode':'accepted_202_late'});click();wait(lambda v:attempt()['outcome']=='delivery_unknown',t=11)
 late=attempt();assert stats(u)['requests']['key']==1 and stats(u)['enqueued']==1 and not eligible()['eligible']
 time.sleep(2);assert attempt()['attempt_id']==late['attempt_id'] and attempt()['outcome']=='delivery_unknown'
 ev("(() => {document.querySelector('[data-key=\"427\"]').click();return true})()")
 assert stats(u)['requests']['key']==1;record('accepted-202-late-stays-unknown-no-retry',u)
 RESULT['passed']=True
finally:
 try:browser('close')
 except Exception:pass
 proc.terminate()
 try:proc.wait(timeout=3)
 except subprocess.TimeoutExpired:proc.kill();proc.wait()
 (OUT/'ATTEMPT-RESULT.json').write_text(json.dumps(RESULT,ensure_ascii=False,indent=2)+'\n')
print('PASS',len(RESULT['cases']),SESSION)
