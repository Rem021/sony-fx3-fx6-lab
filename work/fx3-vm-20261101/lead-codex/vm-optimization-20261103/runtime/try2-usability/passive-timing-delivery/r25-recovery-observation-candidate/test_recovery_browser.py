"""One owned real browser/service, candidate PAGE/server and real wrapper __main__; visual/native fixture oracles are MOCK, never real menu evidence."""
import hashlib,importlib.util,json,os,socket,struct,subprocess,sys,threading,time,uuid,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'evidence/recovery-attempt05';SESSION='fx3-deadline-r25-recovery-cfe93acbf347'
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'operator-helpers'))
import trial_web_r24_review_snapshot as web
import review_snapshot_cli as helper
import planned_prerequisite as prereq

def uid():return str(uuid.uuid4())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def png(r,g,b):
 def ch(k,d):return struct.pack('!I',len(d))+k+d+struct.pack('!I',zlib.crc32(k+d)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('!2I5B',2,2,8,2,0,0,0))+ch(b'IDAT',zlib.compress(b'\0'+bytes([r,g,b])*2+b'\0'+bytes([b,r,g])*2))+ch(b'IEND',b'')
B=png(20,100,200);initial=png(80,40,20)
menu_source=ROOT.parent.parent/'runs/v25gate-n64-r17-c33f8c46/trial-final.png';A=menu_source.read_bytes();assert hashlib.sha256(A).hexdigest()==helper.MENU_SHA
save(ROOT/'EXTRA-FIXTURE-INPUTS-BEFORE.json',{str(menu_source):sha(menu_source)})
RESULT={'scope':__doc__,'session':SESSION,'cases':{}};TRACE=[];counts={};sequence=0;bg_stop=threading.Event();bg=None;browser_started=False
state=web.TrialState('r24-offline-service',3600,32)
def publish(data):
 global sequence
 with state.lock:
  sequence+=1;state.publish(data,{'sequence':sequence,'PNG_sha256':hashlib.sha256(data).hexdigest(),'all_zero_pixels':False,'nonuniform_pixels':True,'width':640 if data==A else 2,'height':480 if data==A else 2})
def fake_received(item):
 # No native code is called. This is the explicit fake-backend receive oracle.
 time.sleep(.04)
 counts['nativeDown']+=1;counts['nativeUp']+=1
 with state.lock:
  state.take();state.update(steps=item['step']);assert state.note_native_received(item['step'],item['request_id'])
  publish(A);state.require_visual_review(item['step'],'visual_changed',True)
 TRACE.append({'fixture_native_receive_oracle':True,'step':item['step'],'attempt_id':item['request_id']})
def submit(body):
 counts['keyPOST']+=1;code,value=web.TrialState.submit(state,body)
 TRACE.append({'keyPOST':True,'status':code,'observed_sequence':body.get('observed_sequence'),'pending':len(state.pending)})
 if code==202:
  item={**state.pending[-1],'step':state.steps+1};threading.Thread(target=fake_received,args=(item,),daemon=True).start()
 return code,value
state.submit=submit
original_confirm=state.confirm_visual

def confirm(body):
 counts['confirmPOST']+=1;code,value=web.TrialState.confirm_visual(state,body)
 TRACE.append({'confirmPOST':True,'status':code,'snapshot_id':body.get('snapshot_id'),'step':body.get('step')})
 return code,value
state.confirm_visual=confirm
server,server_thread=web.start_server(state,0);url=state.url+'/'
# Test-only extra GET route. All PAGE/server key/confirm logic remains the actual candidate.
fixture_original_get=server.RequestHandlerClass.do_GET
def fixture_get(self):
 if self.path=='/fixture/preflight-barrier':
  publish(B);TRACE.append({'fixture_preflight_barrier':True,'sequence':sequence,'generation':state.content_generation});return self.reply(200,{'fixture_only':True})
 return fixture_original_get(self)
server.RequestHandlerClass.do_GET=fixture_get

RESULT.update(server_pid=os.getpid(),port=server.server_address[1])
def browser(*args,source=None):
 p=subprocess.run(['agent-browser','--session',SESSION,*args],input=source,text=True,capture_output=True,timeout=20)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout.strip()
def js(s):return json.loads(browser('eval','--stdin',source=s))
def wait(fn,timeout=6):
 until=time.monotonic()+timeout
 while time.monotonic()<until:
  v=fn()
  if v:return v
  time.sleep(.03)
 raise AssertionError('fixture condition timeout')
def prepare(name):
 global browser_started,sequence,bg,bg_stop
 if bg:bg_stop.set();bg.join();bg=None
 if browser_started:browser('open','about:blank')
 fresh=web.TrialState('r24-offline-'+name,3600,32);fresh.url=state.url
 with state.lock:state.__dict__.update(fresh.__dict__)
 counts.update(keyPOST=0,confirmPOST=0,nativeDown=0,nativeUp=0);sequence=0
 launch=uid();state.update(phase='ready',ready=True,launch_request_id=launch,launch_status='running');publish(initial)
 browser('open',url);browser_started=True;browser('set','viewport','1280','1200')
 wait(lambda:js('!!lastStatus&&frameLoadedFor(lastStatus)&&!keys[0].disabled'))
 if True:
  info=json.loads(browser('session','info','--json'));RESULT['browser_session_info']=info
  rows=[x.split(None,2) for x in subprocess.check_output(['ps','-axo','pid=,ppid=,command='],text=True).splitlines()];owned={info['data']['pid']}
  while True:
   extra={int(x[0]) for x in rows if int(x[1]) in owned}-owned
   if not extra:break
   owned|=extra
  RESULT['owned_browser_pids']=sorted(set(RESULT.get('owned_browser_pids',[]))|owned)
 js((ROOT/'operator-helpers/deadline.js').read_text()+'('+json.dumps({'expectedURL':url,'expectedLaunchId':launch})+')')
 d=OUT/name;d.mkdir();return launch,d

def arm_and_key(launch):
 nonce=uid();js('window.__fx3InteractionDeadlineV1.arm('+json.dumps(nonce)+')')
 js('keys.find(b=>Number(b.dataset.key)===427).click();true')
 wait(lambda:js('currentKeyAttempt?.outcome==="accepted"&&lastStatus?.review_required&&frameLoadedFor(lastStatus)&&canPinReview(lastStatus)'))
 aid=js('currentKeyAttempt.attempt_id');return nonce,aid

def dynamic():
 global bg,bg_stop
 bg_stop=threading.Event();log=[]
 def run():
  started=time.monotonic();toggles=[.4,.8,2.4,3.2,3.6,4.8,5.2,5.6,6.8,7.2,8.8,10.4,10.8,12.4];i=0;data=A
  while not bg_stop.wait(.06):
   elapsed=time.monotonic()-started
   if i<len(toggles) and elapsed>=toggles[i]:data=B if data==A else A;i+=1
   publish(data);log.append({'elapsed':elapsed,'sequence':sequence,'generation':state.content_generation,'sha256':state.frame['PNG_sha256']})
 bg=threading.Thread(target=run);bg.start();return log
REAL_BROWSER='/Users/kafu/.local/bin/agent-browser'
hook_stop=threading.Event();hook_thread=None

def hook(name,action='switch',eval_after=None):
 global hook_thread
 path=OUT/(name+'.hook.json');save(path,{'action':action,'eval_after':eval_after})
 def run():
  signal=path.with_suffix('.signal');done=path.with_suffix('.done');end=time.monotonic()+15
  while not signal.exists() and time.monotonic()<end and not hook_stop.wait(.01):pass
  if not signal.exists():return
  old={'seq':sequence,'gen':state.content_generation,'sha':state.frame['PNG_sha256']}
  if action=='switch':
   data=A if state.frame['PNG_sha256']!=hashlib.sha256(A).hexdigest() else B;publish(data)
   wait(lambda:js('frameLoadedFor(lastStatus)&&displayedGeneration==='+str(state.content_generation)))
  elif action=='launch':
   state.update(launch_request_id=uid())
  elif action=='step':
   state.update(steps=state.steps+1)
  TRACE.append({'fixture_screenshot_barrier':name,'action':action,'before':old,'after':{'seq':sequence,'gen':state.content_generation,'sha':state.frame['PNG_sha256']}})
  done.write_text('fixture barrier complete')
 hook_thread=threading.Thread(target=run);hook_thread.start();return str(path)

def setup_wrapper(name):
 launch,d=prepare(name);run=d/('run-task_'+name)
 p=subprocess.run(['python3','-B',str(ROOT/'prepare_run.py'),'--run-dir',str(run),'--task-id','task_'+name,'--dispatch-id','ctx_offline_fixture','--session',SESSION],capture_output=True,text=True)
 assert p.returncode==0,p.stderr
 fixture_run=d/'fake-run-no-VM';fixture_run.mkdir();save(fixture_run/'trial-web-final-receipt.json',{'fixture_only':True,'not_real_cleanup_evidence':True})
 save(run/'runtime.json',{'url':url,'launch_id':launch,'run':str(fixture_run),'runner_pid':999999})
 return launch,d,run

def process(d,run,name,args,hook_path=None,ok=True):
 env={**os.environ,'FX3_NAV_RUN_DIR':str(run),'PYTHONDONTWRITEBYTECODE':'1','AGENT_BROWSER_NO_VERSION_CHECK':'1','FX3_FIXTURE_REAL_BROWSER':REAL_BROWSER,'PATH':str(ROOT/'evidence/fixture-bin')+':'+os.environ['PATH']}
 if hook_path:env['FX3_FIXTURE_HOOK']=hook_path
 p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=45)
 save(d/(name+'.process.json'),{'argv':args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'fixture_visual_oracle':True,'fixture_native_oracle':True})
 if ok:assert p.returncode==0,(name,p.stdout,p.stderr)
 else:assert p.returncode!=0,(name,p.stdout)
 try:return json.loads(p.stdout)
 except json.JSONDecodeError:return {'returncode':p.returncode}

def operate(d,run,name,*args,**kw):return process(d,run,name,['python3','-B',str(ROOT/'runtime-wrapper/operate.py'),*args],**kw)
def initial_review(d,run):
 process(d,run,'initial-capture',['python3','-B','-c',"import sys;sys.path.insert(0,sys.argv[1]);from untimed_image import snapshot;import json;from common import HERE;print(json.dumps(snapshot('fixture-initial',HERE/'initial-standby',0)))",str(ROOT/'runtime-wrapper')])
 operate(d,run,'initial-review','standby_review','OFFLINE MOCK semantic oracle; no real visual review')

def reject_first():
 js("window.__fixtureHold=true;const originalFetch=window.fetch.bind(window);window.fetch=async(...args)=>{if(window.__fixtureHold&&busy&&currentKeyAttempt?.outcome==='preflight'&&String(args[0]).includes('/api/status')){window.__fixtureHold=false;await originalFetch('/fixture/preflight-barrier');await new Promise(r=>setTimeout(r,550));}return originalFetch(...args)};true")
 class Completed:
  def join(self):pass
 return Completed()

def binding_from_page():
 a=js('fx3KeyAttemptOutcome()');b={k:a[k] for k in ('attempt_id','document_time_origin','launch_request_id','key','base_step','expected_step')};b.update(PNG_sha256=a['frame']['PNG_sha256'],content_generation=a['frame']['content_generation'],sequence=a['frame']['sequence'],nonce=a['alarm_nonce']);return b

def unqueued(launch):
 nonce=uid();js('window.__fx3InteractionDeadlineV1.arm('+json.dumps(nonce)+')')
 t=reject_first();js('keys.find(b=>Number(b.dataset.key)===427).click();true');t.join();wait(lambda:js('currentKeyAttempt?.outcome==="not_posted"&&frameLoadedFor(lastStatus)&&!busy'))
 return nonce,binding_from_page()

try:
 launch,d,run=setup_wrapper('actual_recovery_chain');initial_review(d,run)
 t=reject_first();h=hook('before_cancel_AB')
 first=operate(d,run,'click1-notposted-capture','click','1','fixed plan target; OFFLINE MOCK',hook_path=h);t.join();hook_thread.join()
 assert first['status']=='qualified_recovery_observation' and counts['keyPOST']==0 and counts['nativeDown']==0
 cap_path=Path(first['observation_path']);cap=json.loads(cap_path.read_text());assert cap['frame_changed'] and cap['before']['content_generation']!=cap['after']['content_generation'] and cap['before']['PNG_sha256']!=cap['after']['PNG_sha256']
 old_assert_would_fail=not all(cap['before'][k]==cap['after'][k] for k in ('PNG_sha256','content_generation'))
 assert old_assert_would_fail
 h=hook('after_cancel_AB')
 cancelled=operate(d,run,'independent-reviewed-cancel','recovery_cancel','OFFLINE MOCK explicitly viewed returned pre-cancel observation',hook_path=h);hook_thread.join()
 assert cancelled['status']=='cancelled_unqueued_alarm_only' and counts['keyPOST']==0
 post_path=Path(cancelled['observation_path']);post=json.loads(post_path.read_text());assert post['frame_changed'] and post['before']['content_generation']!=post['after']['content_generation'] and post['before']['PNG_sha256']!=post['after']['PNG_sha256']
 # Real cancel helper enforces per-step replay and total budget before eval.
 a=json.loads((run/'current-attempt.json').read_text());folder=Path(a['path']);b=json.loads((folder/'binding.json').read_text())
 base=['python3','-B',str(ROOT/'operator-helpers/recovery_tools.py'),'cancel','--session',SESSION,'--url',url,'--launch-id',launch,'--nonce',a['nonce'],'--binding',str(folder/'binding.json'),'--review',str(cap_path),'--review-sha',sha(cap_path),'--target','fixture only']
 refused=process(d,run,'repeat-recovery',base+['--ledger',str(run/'ledger.json'),'--out',str(d/'forbidden-repeat')],ok=False);assert refused['cancel_invoked'] is False
 budget=d/'budget-ledger.json';save(budget,{'attempts':[{'attempt_id':b['attempt_id'],'step':1}], 'recoveries':[{'step':2},{'step':3}]})
 refused=process(d,run,'recovery-budget-exhausted',base+['--ledger',str(budget),'--out',str(d/'forbidden-budget')],ok=False);assert refused['cancel_invoked'] is False
 # Actual recovery_review entry rejects file/receipt substitution; failure is terminal.
 # Preserve a valid independent copy for host negative probes without killing positive chain.
 env={**os.environ,'FX3_NAV_RUN_DIR':str(run),'PYTHONDONTWRITEBYTECODE':'1'}
 original_image=Path(post['screenshot_path']).read_bytes();original_receipt=post_path.read_bytes()
 for case,kind in [('image_tamper','image'),('receipt_tamper','receipt'),('cancel_receipt_tamper','cancel')]:
  if kind=='image':Path(post['screenshot_path']).write_bytes(original_image+b'x')
  elif kind=='receipt':post_path.write_text(original_receipt.decode().replace('qualified_recovery_observation','forged_observation'))
  else:
   pending=json.loads((run/'pending-recovery-review.json').read_text());cancel_path=Path(pending['cancel_path']);cancel_raw=cancel_path.read_bytes();cancel_path.write_bytes(cancel_raw+b' ')
  p=subprocess.run(['python3','-B','-c',"import sys;sys.path.insert(0,sys.argv[1]);sys.path.insert(0,sys.argv[2]);from recovery_guard import pending;pending(False)",str(ROOT/'runtime-wrapper'),str(ROOT/'operator-helpers')],env=env,text=True,capture_output=True)
  save(d/(case+'.process.json'),{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});assert p.returncode!=0
  Path(post['screenshot_path']).write_bytes(original_image);post_path.write_bytes(original_receipt)
  if kind=='cancel':cancel_path.write_bytes(cancel_raw)
 # Real JS reader accepts distinct assignment/log timestamps and rejects forged event links.
 cr=json.loads((folder/'recovery-cancel/cancel-result.json').read_text())['browser_result']['alarm_cancel_receipt']
 config={'url':url,'launch_id':launch,'nonce':a['nonce'],'binding':b,'mode':'cancelled','cancel_receipt':cr,'cancel_identity_json':json.loads((folder/'recovery-cancel/cancel-result.json').read_text())['browser_result']['alarm_cancel_identity_json']}
 reader=(ROOT/'operator-helpers/recovery_readonly.js').read_text()
 accepted_clock=js(reader+'('+json.dumps(config)+')');assert accepted_clock['qualified']
 clock_cases={}
 for kind in ('elapsed','nonce'):
  altered=json.loads(json.dumps(config));canonical=json.loads(altered['cancel_identity_json']);event=canonical['events'][-1]
  if kind=='elapsed':event['elapsed_ms']+=1
  else:event['nonce']=uid()
  altered['cancel_identity_json']=json.dumps(canonical);refusal=js(reader+'('+json.dumps(altered)+')');assert refusal['qualified'] is False
  clock_cases[kind]=refusal
 save(d/'cancel-clock-binding-results.json',{'valid':accepted_clock,'cancel_current':cr['current'],'cancel_event':cr['events'][-1],'negative':clock_cases})
 RESULT['cases']['cancel_assignment_log_clock_binding']={'passed':True,'negative':clock_cases}
 review=operate(d,run,'separate-recovery-review','recovery_review','OFFLINE MOCK semantic oracle for distinct returned after-cancel image');assert review['status']=='explicit_recovery_image_reviewed'
 # Actual helper __main__ enforces max10 before click, using valid original prerequisite.
 attempts=d/'attempt-budget-ledger.json';save(attempts,{'attempts':[{'status':'click_invoked'}]*10,'recoveries':[]})
 process(d,run,'attempt-budget-exhausted',['python3','-B',str(ROOT/'operator-helpers/planned_navigation_click.py'),'--session',SESSION,'--url',url,'--launch',launch,'--nonce',uid(),'--plan-sha',prereq.PLAN_SHA,'--step','1','--prerequisite-path',str(run/'step-00-prerequisite.json'),'--ledger',str(attempts),'--receipt',str(d/'forbidden-budget-click.json')],ok=False)
 second=operate(d,run,'new-nonce-click1-postkey-capture','click','1','same fixed plan target after separate recovery review; OFFLINE MOCK');assert second['status']=='qualified_review_snapshot'
 assert second['nonce']!=a['nonce'] and counts['keyPOST']==1 and counts['confirmPOST']==0 and counts['nativeDown']==counts['nativeUp']==1
 snap=second['snapshot'];publish(B);wait(lambda:js('frameLoadedFor(lastStatus)&&displayedGeneration==='+str(state.content_generation)))
 confirmed=operate(d,run,'historical-postkey-confirm','confirm','OFFLINE MOCK explicit semantic review of exact postkey snapshot')
 assert confirmed['status']=='confirmed_and_cancelled' and counts['confirmPOST']==1 and counts['keyPOST']==1
 RESULT['cases']['actual_wrapper_entire_recovery_chain']={'passed':True,'old_cross_generation_assert_would_fail_before_cancel':old_assert_would_fail,'old_cross_generation_assert_would_fail_after_cancel':post['before']['content_generation']!=post['after']['content_generation'],'first_click_keyPOST':0,'two_explicit_planned_clicks_total_keyPOST':counts['keyPOST'],'confirmPOST':counts['confirmPOST'],'nativeDown':counts['nativeDown'],'nativeUp':counts['nativeUp'],'postkey_snapshot_generation':snap['content_generation'],'confirm_live_generation':state.content_generation,'real_visual_semantics':False,'real_native':False}
 save(d/'observation.json',RESULT['cases']['actual_wrapper_entire_recovery_chain'])

 # Actual wrapper main rejects reuse after recovery already consumed by a distinct click.
 operate(d,run,'repeated-recovery-review-main','recovery_review','fixture replay must fail',ok=False)
 assert counts['keyPOST']==1 and counts['confirmPOST']==1
 RESULT['cases']['wrapper_recovery_review_replay_End']={'passed':True,'counts':dict(counts)}

 # Actual capture helper CLI with screenshot interleavings, no synthetic success receipts.
 for name,action,code in [('document','switch','location.reload();true'),('launch','launch',None),('step','step',None),('attempt','switch','currentKeyAttempt.attempt_id=crypto.randomUUID();true'),('unknown','switch','deliveryUnknown=true;true'),('End','switch','endButton.click();true')]:
  launch,d=prepare('reject_'+name);nonce,b=unqueued(launch);bp=d/'binding.json';save(bp,b);h=hook('reject_'+name,action,code)
  r=process(d,d,'capture-main',['python3','-B',str(ROOT/'operator-helpers/recovery_tools.py'),'capture','--session',SESSION,'--url',url,'--launch-id',launch,'--nonce',nonce,'--binding',str(bp),'--out',str(d/'capture')],hook_path=h,ok=False);hook_thread.join()
  assert r['status'] in ('unknown','refused') and counts['keyPOST']==counts['confirmPOST']==counts['nativeDown']==0
  js('if(!ending&&!finished)endButton.click();true')
  RESULT['cases']['capture_interleaving_'+name]={'passed':True,'status':r['status'],'counts':dict(counts)}

 launch,d=prepare('cancel_wrong_nonce');nonce,b=unqueued(launch);bp=d/'binding.json';save(bp,b)
 cap=process(d,d,'capture-main',['python3','-B',str(ROOT/'operator-helpers/recovery_tools.py'),'capture','--session',SESSION,'--url',url,'--launch-id',launch,'--nonce',nonce,'--binding',str(bp),'--out',str(d/'capture')]);assert cap['status']=='qualified_recovery_observation'
 ledger=d/'ledger.json';save(ledger,{'attempts':[{'attempt_id':b['attempt_id'],'step':1}],'recoveries':[]})
 r=process(d,d,'cancel-wrong-nonce',['python3','-B',str(ROOT/'operator-helpers/recovery_tools.py'),'cancel','--session',SESSION,'--url',url,'--launch-id',launch,'--nonce',uid(),'--binding',str(bp),'--review',str(d/'capture/observation-result.json'),'--review-sha',sha(d/'capture/observation-result.json'),'--target','fixture','--ledger',str(ledger),'--out',str(d/'cancel')],ok=False)
 assert counts['keyPOST']==0 and js('window.__fx3InteractionDeadlineV1.status().current.state')=='armed'
 RESULT['cases']['wrong_nonce_no_cancel']={'passed':True,'counts':dict(counts)};js('endButton.click();true')

 launch,d,run=setup_wrapper('unknown_wrapper_End');initial_review(d,run)
 js('deliveryUnknown=true;disableKeys();true')
 operate(d,run,'unknown-click-main','click','1','fixture unknown must End; never retry',ok=False)
 assert counts['keyPOST']==counts['confirmPOST']==counts['nativeDown']==0 and state.phase in ('stopping','finished')
 RESULT['cases']['wrapper_unknown_End_zero_POST']={'passed':True,'phase':state.phase,'counts':dict(counts)}
 RESULT['passed']=True
finally:
 hook_stop.set()
 if hook_thread:hook_thread.join(timeout=2)
 if bg:bg_stop.set();bg.join()
 if browser_started:
  try:RESULT['browser_close']=browser('close')
  except BaseException as e:RESULT['browser_close_error']=repr(e)
 server.shutdown();server.server_close();server_thread.join(timeout=2);RESULT['server_thread_alive']=server_thread.is_alive()
 with socket.socket() as sock:RESULT['port_connect_ex_after_close']=sock.connect_ex(('127.0.0.1',RESULT['port']))
 RESULT['owned_pid_alive_after']={}
 for pid in RESULT.get('owned_browser_pids',[]):
  try:os.kill(pid,0);alive=True
  except ProcessLookupError:alive=False
  RESULT['owned_pid_alive_after'][str(pid)]=alive
 save(OUT/'HTTP-PROTOCOL-TRACE.json',TRACE);save(OUT/'BROWSER-RESULT.json',RESULT)
print(json.dumps({'passed':RESULT.get('passed'),'groups':len(RESULT['cases']),'port_closed':RESULT['port_connect_ex_after_close']!=0,'owned_pid_alive_after':RESULT['owned_pid_alive_after']}))
assert RESULT.get('passed') and not RESULT['server_thread_alive'] and RESULT['port_connect_ex_after_close']!=0 and not any(RESULT['owned_pid_alive_after'].values())
