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
ready=OUT/'fixture-ready.json';ready.unlink(missing_ok=True)
proc=subprocess.Popen([sys.executable,'-u',str(ROOT/'tests/race_harness.py'),'--module',str(ROOT/'trial_web_v22_navigation_review.py'),'--ready-file',str(ready)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
try:
 until=time.monotonic()+5
 while not ready.exists() and time.monotonic()<until:time.sleep(.03)
 assert ready.exists();urls=json.loads(ready.read_text());web=urls['web'];u=urls['control']
 # Server state advances after click but before one read-only preflight.
 reset(u);initial_sha=page()['shownSHA'];hold();click();wait(lambda v:v['held']);control(u,'publish',{'color':'B'});wait(lambda v:v['displayedGeneration']==2 and v['held'] and v['shownSHA']!=initial_sha and v['statusSHA']==v['shownSHA'] and v['statusGeneration']==2);release();wait(lambda v:v['displayed']==2 and not v['disabled']);record('old-view-no-post-new-B',u);assert stats(u)['requests']['key']==0
 click();wait(lambda v:stats(u)['requests']['key']==1);record('manual-B-one-post',u);assert stats(u)['enqueued']==1
 # Matching preflight leads to exactly one post.
 reset(u);click();wait(lambda v:stats(u)['requests']['key']==1);record('matching-one-post',u);assert stats(u)['enqueued']==1
 # A -> B -> A has the same bytes but a new generation; never reuse the click.
 reset(u);hold();click();wait(lambda v:v['held']);control(u,'publish',{'color':'B'});control(u,'publish',{'color':'A'});wait(lambda v:v['displayedGeneration']==3 and v['held'] and v['statusSHA']==v['shownSHA'] and v['statusGeneration']==3);release();wait(lambda v:v['displayedGeneration']==3 and not v['disabled']);record('ABA-during-GET-zero-post',u);assert stats(u)['requests']['key']==0
 # Identical content with only sequence advancing may still use the original click.
 reset(u);hold();click();wait(lambda v:v['held']);control(u,'publish',{'color':'A'});release();wait(lambda v:stats(u)['requests']['key']==1);record('same-content-seq-forward-one-post',u);assert stats(u)['enqueued']==1
 # A server change after preflight still invokes the original 409 gate.
 reset(u);control(u,'mode',{'mode':'stale_sha'});click();wait(lambda v:'本次按键未被接收' in v['summary']);record('post-preflight-server-409',u);assert stats(u)['requests']['key']==1 and stats(u)['enqueued']==0
 # Synchronous double click reserves the first operation before await.
 reset(u);hold();ev('(() => {let b=document.querySelector(\'[data-key="427"]\');b.click();b.click();return true})()');wait(lambda v:v['held']);release();wait(lambda v:stats(u)['requests']['key']==1);record('double-click-one-post',u)
 # Unknown POST remains locked; no auto retry.
 reset(u);control(u,'mode',{'mode':'http500'});click();wait(lambda v:v['deliveryUnknown']);record('unknown-no-retry',u);assert stats(u)['requests']['key']==1 and stats(u)['enqueued']==0
 # Read-only GET failure never posts a mutation; next successful tick can recover.
 reset(u)
 ev("(() => {const old=window.fetch.bind(window);let used=false;window.fetch=(url,opt)=>{if(!used&&busy&&String(url).includes('/api/status')){used=true;return Promise.reject(Error('fixture GET failure'));}return old(url,opt);};return true})()")
 click();wait(lambda v: not v['busy']);record('preflight-GET-failed-zero-post',u);assert stats(u)['requests']['key']==0
 reset(u);hold();click();wait(lambda v:v['held']);wait(lambda v:not v['busy'] and not v['disabled'],t=11);record('preflight-GET-timeout-zero-post',u);assert stats(u)['requests']['key']==0;release();time.sleep(.2);assert stats(u)['requests']['key']==0;click();wait(lambda v:stats(u)['requests']['key']==1);record('post-timeout-manual-click-one-post',u);assert stats(u)['enqueued']==1
 # End during held preflight cannot send a key.
 reset(u);hold();click();wait(lambda v:v['held']);ev('(() => {document.querySelector("#end").click();return true})()');release();wait(lambda v:v['ending']);record('End-during-preflight-zero-post',u);assert stats(u)['requests']['key']==0
 # Normal review confirmation keeps its original handler and adds no key.
 reset(u);click();wait(lambda v: not v['confirmDisabled']);ev('(() => {document.querySelector("#confirm").click();return true})()');wait(lambda v:stats(u)['requests']['confirm']==1);record('confirm-original-one-request',u);assert stats(u)['requests']['key']==1
 # No-frame launch remains available and does not write a key.
 control(u,'awaiting-launch');browser('open',web);wait(lambda v:not v['startDisabled']);record('no-frame-Start-available',u);assert stats(u)['requests']['key']==0
 RESULT['passed']=True
finally:
 try:browser('close')
 except Exception:pass
 proc.terminate()
 try:proc.wait(timeout=3)
 except subprocess.TimeoutExpired:proc.kill();proc.wait()
 (OUT/'BROWSER-RESULT.json').write_text(json.dumps(RESULT,ensure_ascii=False,indent=2)+'\n')
print('PASS',len(RESULT['cases']),SESSION)
