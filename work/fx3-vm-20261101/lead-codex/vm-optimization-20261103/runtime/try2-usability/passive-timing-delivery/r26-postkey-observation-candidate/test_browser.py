"""One owned real browser/service, candidate PAGE/server and real wrapper __main__; visual/native fixture oracles are MOCK, never real menu evidence."""
import hashlib,importlib.util,json,os,socket,struct,subprocess,sys,threading,time,uuid,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'evidence/browser-attempt04';SESSION='fx3-deadline-r26-4603590349ac'
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
MENU_DELAY=0.0;NATIVE_TIME=None;ANIMATION=[]
def fake_received(item):
 global NATIVE_TIME,bg,bg_stop
 time.sleep(.04);NATIVE_TIME=time.monotonic();counts['nativeDown']+=1;counts['nativeUp']+=1
 with state.lock:
  state.take();state.update(steps=item['step']);assert state.note_native_received(item['step'],item['request_id'])
  publish(initial if MENU_DELAY else A);state.require_visual_review(item['step'],'visual_changed',True)
 TRACE.append({'fixture_native_receive_oracle':True,'step':item['step'],'attempt_id':item['request_id'],'host_monotonic':NATIVE_TIME})
 if MENU_DELAY:
  bg_stop=threading.Event()
  def animate():
   while not bg_stop.wait(.08):
    elapsed=time.monotonic()-NATIVE_TIME
    data=A if elapsed>=MENU_DELAY else (initial if int(elapsed/.7)%2==0 else B)
    publish(data);ANIMATION.append({'elapsed_after_native':elapsed,'sequence':sequence,'generation':state.content_generation,'sha':state.frame['PNG_sha256']})
    if elapsed>=MENU_DELAY:break
  bg=threading.Thread(target=animate);bg.start()
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
def pin(body):
 counts['pinPOST']+=1;code,value=web.TrialState.pin_review(state,body);TRACE.append({'pinPOST':True,'status':code,'step':body.get('step'),'attempt_id':body.get('attempt_id'),'host_monotonic':time.monotonic()});return code,value
state.pin_review=pin

server,server_thread=web.start_server(state,0);url=state.url+'/'
# Test-only extra GET route. All PAGE/server key/confirm logic remains the actual candidate.
fixture_original_get=server.RequestHandlerClass.do_GET
def fixture_get(self):
 if self.path=='/fixture/change-launch':
  state.update(launch_request_id=uid());return self.reply(200,{'fixture_only':True})
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
 counts.update(keyPOST=0,confirmPOST=0,pinPOST=0,nativeDown=0,nativeUp=0);sequence=0
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

def accepted_wrapper(name,delay=0):
 global MENU_DELAY,ANIMATION
 MENU_DELAY=delay;ANIMATION=[]
 launch,d,run=setup_wrapper(name);initial_review(d,run)
 first=operate(d,run,'click-observe1','click','1','OFFLINE MOCK predetermined MENU target')
 assert first['status']=='qualified_unpinned_postkey_observation' and counts['keyPOST']==1 and counts['pinPOST']==counts['confirmPOST']==0
 return launch,d,run,first

def fixed(d,run):
 pin=operate(d,run,'explicit-pin','pin','OFFLINE MOCK actually observed complete target, select a new fixed snapshot')
 assert pin['status']=='qualified_review_snapshot' and counts['pinPOST']==1
 return pin

def summary(name,d,extra=None):
 x={'passed':True,'counts':dict(counts),'visual_semantics':'MOCK','native':'MOCK',**(extra or {})};RESULT['cases'][name]=x;save(d/(name+'.json'),x)

try:
 # 4.5-second native-to-interface delay, with real non-zero separate tool/review intervals.
 launch,d,run,first=accepted_wrapper('delayed_4500ms_three_observations',4.5)
 assert first['before']['displayed_frame']['PNG_sha256'] in (hashlib.sha256(initial).hexdigest(),hashlib.sha256(B).hexdigest())
 assert state.review_object is None and state.active_input['review_state']=='unissued'
 first_return=time.monotonic();time.sleep(.8)
 second=operate(d,run,'separate-observe2','observe','OFFLINE MOCK viewed first observation: normal standby animation, explicitly observe again')
 assert second['observation_number']==2 and counts['pinPOST']==0 and state.review_object is None
 # Model/tool interval remains charged against the same original 20s alarm.
 time.sleep(max(.8,4.5-(time.monotonic()-NATIVE_TIME)+.5))
 third=operate(d,run,'separate-observe3','observe','OFFLINE MOCK viewed second observation: wait transition through another explicit observation')
 assert third['observation_number']==3 and third['before']['displayed_frame']['PNG_sha256']==hashlib.sha256(A).hexdigest() and counts['pinPOST']==0
 time.sleep(.65);pinned=fixed(d,run);assert pinned['screenshot_sha256']==hashlib.sha256(A).hexdigest()
 assert Path(pinned['screenshot_path'])!=Path(third['screenshot_path']) and pinned['snapshot']['snapshot_id']
 time.sleep(.8)
 confirmed=operate(d,run,'independent-fixed-image-confirm','confirm','OFFLINE MOCK separately viewed actual fixed PNG, complete target confirmed')
 assert confirmed['status']=='confirmed_and_cancelled' and counts['keyPOST']==counts['pinPOST']==counts['confirmPOST']==counts['nativeDown']==counts['nativeUp']==1
 alarm=js('window.__fx3InteractionDeadlineV1.status()');elapsed=alarm['events'][-1]['elapsed_ms'];assert 4500<elapsed<20000 and alarm['current']['state']=='cancelled'
 save(d/'animation-schedule.json',ANIMATION)
 summary('actual_wrapper_4500ms_observe_observe_observe_pin_confirm',d,{'native_to_first_observation_return_seconds':first_return-NATIVE_TIME,'configured_menu_delay_seconds':4.5,'native_to_menu_first_publish_seconds':min(x['elapsed_after_native'] for x in ANIMATION if x['sha']==hashlib.sha256(A).hexdigest()),'deadline_ms':alarm['deadline_ms'],'actual_alarm_elapsed_ms':elapsed,'displayed_frame_SHAs_before_observations':[x['before']['displayed_frame']['PNG_sha256'] for x in (first,second,third)],'actual_observation_screenshot_SHAs':[x['screenshot_sha256'] for x in (first,second,third)],'snapshot_id':pinned['snapshot']['snapshot_id'],'nonzero_explicit_review_sleeps_seconds':[.8,.65,.8]})
 # A second planned step proves next-key historical prerequisite still works.
 MENU_DELAY=0
 next_obs=operate(d,run,'step2-click-observe','click','2','OFFLINE MOCK next fixed plan target')
 assert next_obs['status']=='qualified_unpinned_postkey_observation' and counts['keyPOST']==2
 next_pin=operate(d,run,'step2-explicit-pin','pin','OFFLINE MOCK separately observed next target complete')
 next_confirm=operate(d,run,'step2-independent-confirm','confirm','OFFLINE MOCK separately viewed step2 fixed PNG')
 assert next_confirm['status']=='confirmed_and_cancelled' and counts['keyPOST']==counts['pinPOST']==counts['confirmPOST']==2
 summary('actual_second_step_prerequisite',d)

 # Reproduce the old early-pin issue with unchanged capture helper and actual server.
 MENU_DELAY=4.5;launch,d=prepare('old_early_pin_reproducer');nonce,aid=arm_and_key(launch)
 early=helper.capture(SESSION,url,launch,nonce,1,aid,d/'early-capture')
 assert early['status']=='qualified_review_snapshot' and early['snapshot']['PNG_sha256']!=hashlib.sha256(A).hexdigest()
 time.sleep(max(.1,4.5-(time.monotonic()-NATIVE_TIME)+.25))
 assert state.frame['PNG_sha256']==hashlib.sha256(A).hexdigest() and state.review_object['meta']==early['snapshot']
 summary('old_automatic_first_frame_would_pin_standby',d,{'early_snapshot_sha':early['snapshot']['PNG_sha256'],'later_live_menu_sha':state.frame['PNG_sha256'],'confirmed':False});js('endButton.click();true');MENU_DELAY=0

 # Required original unqueued recovery chain, then r26 new observe/pin/confirm flow.
 launch,d,run=setup_wrapper('recovery_then_new_postkey_flow');initial_review(d,run);reject_first()
 failed=operate(d,run,'notposted-recovery-image','click','1','OFFLINE MOCK first explicit key legally refused')
 assert failed['status']=='qualified_recovery_observation' and counts['keyPOST']==0
 cancelled=operate(d,run,'independent-recovery-cancel','recovery_cancel','OFFLINE MOCK viewed recovery image, cancel same unqueued nonce only')
 reviewed=operate(d,run,'independent-recovery-review','recovery_review','OFFLINE MOCK viewed new cancelled recovery observation')
 newobs=operate(d,run,'new-nonce-click-observe','click','1','OFFLINE MOCK same predetermined target after reviewed recovery')
 assert newobs['status']=='qualified_unpinned_postkey_observation' and counts['keyPOST']==1 and counts['pinPOST']==0
 fixed(d,run);operate(d,run,'new-fixed-confirm','confirm','OFFLINE MOCK independently viewed new fixed PNG')
 assert counts['keyPOST']==counts['pinPOST']==counts['confirmPOST']==counts['nativeDown']==counts['nativeUp']==1
 summary('r25_recovery_full_chain_to_r26_observe_pin_confirm',d)

 # Wrong reader identities through the actual helper __main__, each one-use reservation.
 launch,d,run,obs=accepted_wrapper('wrong_observation_bindings')
 a=json.loads((run/'current-attempt.json').read_text());flow=json.loads((Path(a['path'])/'postkey-flow.json').read_text());binding=flow['binding'];negative={}
 for key,value in [('attempt_id',uid()),('document_id',uid()),('launch_id',uid()),('step',2),('nonce',uid()),('run_incarnation',uid()),('document_time_origin',binding['document_time_origin']+1)]:
  b={**binding,key:value};bp=d/('wrong-'+key+'.json');save(bp,b);reservation=d/('reservation-'+key+'.json');save(reservation,{'status':'reserved_unknown','reservation_id':uid(),'observation_number':2,'binding':b})
  result=process(d,run,'wrong-'+key,['python3','-B',str(ROOT/'operator-helpers/postkey_observation.py'),'--session',SESSION,'--binding',str(bp),'--reservation',str(reservation),'--out',str(d/('out-'+key))],ok=False)
  assert result['status']=='unknown' and not (d/('out-'+key)/'observation.png').exists();negative[key]=result['status']
 assert counts['keyPOST']==1 and counts['pinPOST']==counts['confirmPOST']==0
 summary('actual_observation_helper_identity_negatives',d,{'negative':negative});js('endButton.click();true')

 # Real wrapper negative actions each terminate the run, no pin/confirm/key replay.
 for case in ('confirm_without_pin','observation_masquerade','fourth_observation','observe_after_pin','repin','lost_confirm_reply','screenshot_unknown','screenshot_launch_change','screenshot_End','tampered_observation'):
  launch,d,run,obs=accepted_wrapper(case)
  if case=='confirm_without_pin':operate(d,run,'reject-confirm','confirm','fixture must not confirm an observation',ok=False)
  elif case=='observation_masquerade':
   a=json.loads((run/'current-attempt.json').read_text());save(Path(a['path'])/'validated-image-return.json',obs)
   operate(d,run,'reject-observation-as-fixed','confirm','fixture forged observation cannot be fixed evidence',ok=False)
  elif case=='fourth_observation':
   operate(d,run,'observe2','observe','OFFLINE MOCK normal transition; explicit second observation')
   operate(d,run,'observe3','observe','OFFLINE MOCK normal transition; explicit third observation')
   operate(d,run,'reject-observe4','observe','fixture exhausted, must End',ok=False)
  elif case=='observe_after_pin':
   fixed(d,run);operate(d,run,'reject-observe-after-pin','observe','fixture cannot observe after fixed selection',ok=False)
  elif case=='repin':
   fixed(d,run);operate(d,run,'reject-repin','pin','fixture cannot replace fixed snapshot',ok=False)
  elif case=='lost_confirm_reply':
   fixed(d,run)
   js("const originalFetch=window.fetch.bind(window);window.fetch=async(...args)=>{const response=await originalFetch(...args);if(String(args[0]).includes('/api/confirm-visual'))throw Error('FIXTURE lost reply after server mutation');return response};true")
   operate(d,run,'lost-confirm-reply-End','confirm','OFFLINE MOCK fixed view reviewed; reply lost remains unknown',ok=False)
   assert counts['confirmPOST']==1
  elif case in ('screenshot_unknown','screenshot_launch_change','screenshot_End'):
   action='launch' if case=='screenshot_launch_change' else 'switch'
   code='endButton.click();true' if case=='screenshot_End' else ('deliveryUnknown=true;true' if case=='screenshot_unknown' else None)
   h=hook(case,action,code)
   operate(d,run,'reject-async-'+case,'observe','OFFLINE MOCK next explicit observation; screenshot identity changes must End',hook_path=h,ok=False);hook_thread.join()

  else:
   Path(obs['screenshot_path']).write_bytes(Path(obs['screenshot_path']).read_bytes()+b'tamper')
   operate(d,run,'reject-tampered-observation','pin','fixture bad PNG cannot authorize selection',ok=False)
  assert counts['keyPOST']==counts['nativeDown']==counts['nativeUp']==1 and counts['pinPOST']<=1 and counts['confirmPOST']<=1
  assert (run/'POSTKEY-TERMINAL.json').exists() and state.phase in ('stopping','finished')
  flow=json.loads((Path(json.loads((run/'current-attempt.json').read_text())['path'])/'postkey-flow.json').read_text());assert flow['status']=='terminal'
  summary('wrapper_End_'+case,d)

 # The original alarm expires naturally. No retime or fabricated performance clock.
 launch,d,run,obs=accepted_wrapper('expired_observation_retry')
 remaining=js('window.__fx3InteractionDeadlineV1.status().current.due_ms-performance.now()')
 time.sleep(max(0,remaining/1000)+.15)
 operate(d,run,'reject-observe-after-original-deadline','observe','fixture late retry must End, no new alarm',ok=False)
 assert counts['keyPOST']==1 and counts['pinPOST']==counts['confirmPOST']==0 and (run/'POSTKEY-TERMINAL.json').exists()
 summary('original_20s_expiry_retry_End',d,{'waited_original_remaining_ms':remaining})
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
