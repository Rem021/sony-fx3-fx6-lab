"""One owned real browser/service, candidate PAGE/server and real wrapper __main__; visual/native fixture oracles are MOCK, never real menu evidence."""
import hashlib,importlib.util,json,os,socket,struct,subprocess,sys,threading,time,uuid,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'evidence';SESSION='fx3-deadline-r24-88155b8e5e5c'
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
 counts.update(keyPOST=0,confirmPOST=0);sequence=0
 launch=uid();state.update(phase='ready',ready=True,launch_request_id=launch,launch_status='running');publish(initial)
 browser('open',url);browser_started=True;browser('set','viewport','1280','1200')
 wait(lambda:js('!!lastStatus&&frameLoadedFor(lastStatus)&&!keys[0].disabled'))
 if 'owned_browser_pids' not in RESULT:
  info=json.loads(browser('session','info','--json'));RESULT['browser_session_info']=info
  rows=[x.split(None,2) for x in subprocess.check_output(['ps','-axo','pid=,ppid=,command='],text=True).splitlines()];owned={info['data']['pid']}
  while True:
   extra={int(x[0]) for x in rows if int(x[1]) in owned}-owned
   if not extra:break
   owned|=extra
  RESULT['owned_browser_pids']=sorted(owned)
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

try:
 launch,d=prepare('wrapper_dynamic_historical')
 run=d/'run-fixture_wrapper';p=subprocess.run(['python3','-B',str(ROOT/'prepare_run.py'),'--run-dir',str(run),'--task-id','task_fixture_wrapper','--dispatch-id','ctx_offline_fixture','--session',SESSION],capture_output=True,text=True);assert p.returncode==0,p.stderr
 env={**os.environ,'FX3_NAV_RUN_DIR':str(run),'PYTHONDONTWRITEBYTECODE':'1'}
 fixture_run=d/'fake-run-no-VM';fixture_run.mkdir();save(fixture_run/'trial-web-final-receipt.json',{'fixture_only':True,'not_real_cleanup_evidence':True})
 save(run/'runtime.json',{'url':url,'launch_id':launch,'run':str(fixture_run),'runner_pid':999999})
 def process(name,args,timeout=35):
  p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=timeout);save(d/(name+'.process.json'),{'argv':args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'fixture_visual_oracle':True})
  assert p.returncode==0,(name,p.stdout,p.stderr);return json.loads(p.stdout)
 # Actual pinned initial screenshot, then explicit MOCK semantic oracle through actual wrapper __main__.
 process('initial-capture',['python3','-B','-c',"import sys;sys.path.insert(0,sys.argv[1]);from untimed_image import snapshot;import json;from common import HERE;print(json.dumps(snapshot('fixture-initial',HERE/'initial-standby',0)))",str(ROOT/'runtime-wrapper')])
 process('standby-review',['python3','-B',str(ROOT/'runtime-wrapper/operate.py'),'standby_review','FIXTURE semantic oracle only; no real standby/menu review'])
 first=process('click1',['python3','-B',str(ROOT/'runtime-wrapper/operate.py'),'click','1','fixed plan target; fixture pixels not real menu proof'])
 first_meta=first['snapshot'];assert counts['keyPOST']==1 and counts['confirmPOST']==0 and state.review_required
 updates=dynamic();started=time.monotonic();bg_stop.wait(9.3066);elapsed=time.monotonic()-started
 assert elapsed>=9.3066 and first_meta['observed_sequence'] not in state.frames and len(state.frames)==64
 assert state.review_object['meta']==first_meta and state.review_object['png']==A
 assert state.content_generation>first_meta['content_generation']
 historical=process('confirm1',['python3','-B',str(ROOT/'runtime-wrapper/operate.py'),'confirm','FIXTURE explicit historical image semantic oracle; not real menu evidence'])
 assert historical['status']=='confirmed_and_cancelled' and counts['confirmPOST']==1
 receipt=json.loads((run/'step-01-confirm.json').read_text());assert receipt['browser_result']['expected']['content_generation']==first_meta['content_generation']
 assert receipt['browser_result']['expected']['observed_sequence']==first_meta['observed_sequence']
 second=process('click2',['python3','-B',str(ROOT/'runtime-wrapper/operate.py'),'click','2','fixed plan target 2; fixture only'])
 assert second['status']=='qualified_review_snapshot' and counts['keyPOST']==2 and counts['confirmPOST']==1
 assert second['snapshot']['attempt_id']!=first_meta['attempt_id']
 save(d/'observation.json',{'passed':True,'external_review_delay_seconds':elapsed,'historical_snapshot':first_meta,'live_generation_after_next_capture':state.content_generation,'dynamic_publishes':len(updates),'frames_len':len(state.frames),'actual_wrapper_main':True,'keyPOST':counts['keyPOST'],'confirmPOST':counts['confirmPOST'],'real_visual_semantics':False})
 save(d/'dynamic-publishes.json',updates)
 RESULT['cases']['wrapper_dynamic_capture_confirm_next']=json.loads((d/'observation.json').read_text())
 # Real accepted capture/confirm base with deliberately substituted self-consistent visual files.
 original_pr=json.loads((run/'step-01-prerequisite.json').read_text());original_cap=json.loads(Path(original_pr['observation_path']).read_text())
 negatives={}
 for name in ['other_png','other_document_origin','other_document_id']:
  nd=d/name;nd.mkdir();im=nd/'capture';im.mkdir();shot=im/'review-snapshot.png';shot.write_bytes(B if name=='other_png' else A)
  cap={**original_cap,'screenshot_path':str(shot),'screenshot_sha256':sha(shot)}
  if name=='other_document_origin':cap['document_time_origin']+=1
  if name=='other_document_id':cap['pin_result']={**cap['pin_result'],'document_id':uid()}
  cp=nd/'validated-image-return.json';save(cp,cap);v={**original_pr,'observation_path':str(cp),'observation_sha256':sha(cp)};pr=nd/'prerequisite.json';save(pr,v)
  try:prereq.prerequisite(pr,2,launch)
  except ValueError as e:negatives[name]={'refused':True,'reason':str(e)}
  else:raise AssertionError('unrelated visual evidence accepted')
 save(d/'prerequisite-negative-results.json',negatives);RESULT['cases']['exact_image_and_document_negative_bindings']=negatives
 # Actual helper __main__ cannot progress to step3 without the second explicit confirmation.
 p=subprocess.run(['python3','-B',str(ROOT/'operator-helpers/planned_navigation_click.py'),'--session',SESSION,'--url',url,'--launch',launch,'--nonce',uid(),'--plan-sha',prereq.PLAN_SHA,'--step','3','--prerequisite-path',str(run/'step-02-prerequisite.json'),'--ledger',str(run/'ledger.json'),'--receipt',str(run/'forbidden-step3.json')],capture_output=True,text=True)
 save(d/'unconfirmed-next-main.process.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});assert p.returncode==2 and counts['keyPOST']==2
 RESULT['cases']['unconfirmed_step3_no_action']={'passed':True,'keyPOST':counts['keyPOST']}

 launch,d=prepare('confirm_reply_lost')
 nonce,aid=arm_and_key(launch);cap=helper.capture(SESSION,url,launch,nonce,1,aid,d/'capture');assert cap['status']=='qualified_review_snapshot'
 js("const realFetch=window.fetch.bind(window);window.fetch=async(...args)=>{const r=await realFetch(...args);if(String(args[0]).includes('/api/confirm-visual'))throw Error('fixture response lost');return r};true")
 rec=helper.confirm(SESSION,url,launch,nonce,1,aid,d/'capture/capture-result.json','fixture protocol oracle only',d/'confirm.json');assert rec['status']=='unknown'
 wait(lambda:js('reviewProtocolUnknown&&reviewUnknown'))
 js('confirmButton.click();true');assert counts['confirmPOST']==1 and state.review_object is None
 assert js('keys.every(b=>b.disabled)')
 RESULT['cases']['lost_confirm_reply_no_repeat']={'passed':True,'receipt':rec['status'],'confirmPOST':counts['confirmPOST'],'page':js('fx3ReviewSnapshotState()')}
 save(d/'observation.json',RESULT['cases']['lost_confirm_reply_no_repeat'])

 launch,d=prepare('delayed_confirm_vs_End')
 nonce,aid=arm_and_key(launch);cap=helper.capture(SESSION,url,launch,nonce,1,aid,d/'capture');assert cap['status']=='qualified_review_snapshot'
 js("const realFetch=window.fetch.bind(window);window.fetch=async(...args)=>{const r=await realFetch(...args);if(String(args[0]).includes('/api/confirm-visual')){setTimeout(()=>endButton.click(),20);await new Promise(x=>setTimeout(x,180));}return r};true")
 rec=helper.confirm(SESSION,url,launch,nonce,1,aid,d/'capture/capture-result.json','fixture protocol oracle only',d/'confirm.json');assert rec['status']=='unknown'
 wait(lambda:js('reviewTerminated&&ending'));time.sleep(.25)
 page_state=js('fx3ReviewSnapshotState()');assert page_state['snapshot'] is None and page_state['last_ack'] is None and state.review_object is None and js('keys.every(b=>b.disabled)')
 RESULT['cases']['late_confirm_cannot_restore_terminal']={'passed':True,'page':page_state,'server_phase':state.phase,'confirmPOST':counts['confirmPOST']};save(d/'observation.json',RESULT['cases']['late_confirm_cannot_restore_terminal'])

 launch,d=prepare('delayed_pin_vs_End')
 nonce,aid=arm_and_key(launch)
 js("const realFetch=window.fetch.bind(window);window.fetch=async(...args)=>{const r=await realFetch(...args);if(String(args[0]).includes('/api/review-snapshot')){setTimeout(()=>endButton.click(),20);await new Promise(x=>setTimeout(x,180));}return r};true")
 cap=helper.capture(SESSION,url,launch,nonce,1,aid,d/'capture');assert cap['status']=='unknown'
 time.sleep(.25);page_state=js('fx3ReviewSnapshotState()');assert page_state['snapshot'] is None and state.review_object is None and js('keys.every(b=>b.disabled)')
 RESULT['cases']['late_pin_cannot_restore_terminal']={'passed':True,'page':page_state,'server_phase':state.phase};save(d/'observation.json',RESULT['cases']['late_pin_cannot_restore_terminal'])
 RESULT['passed']=True
finally:
 if bg:bg_stop.set();bg.join()
 if browser_started:
  try:RESULT['browser_close']=browser('close')
  except BaseException as e:RESULT['browser_close_error']=type(e).__name__
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
