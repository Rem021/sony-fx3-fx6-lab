"""One owned offline browser/service. Fixture prerequisites are an explicit mocked oracle, NOT real visual reviews."""
import hashlib,importlib.util,json,os,socket,struct,subprocess,sys,threading,time,uuid,zlib
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'evidence';OLD=ROOT.parent/'v25-r21-recovery-integration'
SESSION='fx3-deadline-r23-4581997e3569'
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'operator-helpers'))
import planned_navigation_click as candidate
spec=importlib.util.spec_from_file_location('original_page',OLD/'trial_web_v22_navigation_review.py');page=importlib.util.module_from_spec(spec);spec.loader.exec_module(page)
RESULT={'scope':'offline scripted protocol fixture; real PAGE/server; historical prerequisite oracle mocked, no human/agent semantic review claimed','session':SESSION,'cases':{}}
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def png(r,g,b):
 def ch(k,d):return struct.pack('!I',len(d))+k+d+struct.pack('!I',zlib.crc32(k+d)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('!2I5B',2,2,8,2,0,0,0))+ch(b'IDAT',zlib.compress(b'\0'+bytes([r,g,b])*2+b'\0'+bytes([b,r,g])*2))+ch(b'IEND',b'')
A=png(80,40,20);B=png(20,100,200)
assert hashlib.sha256(page.PAGE.split('<script>')[1].split('</script>')[0].encode()).hexdigest()==candidate.PAGE_SHA
state=page.TrialState('r23-offline-only',3600,4096);submit_original=state.submit
counts={};race=False;TRACE=[]
def publish(data,seq):state.publish(data,{'sequence':seq,'PNG_sha256':hashlib.sha256(data).hexdigest(),'all_zero_pixels':False,'width':2,'height':2})
def submit(body):
 counts['keyPOST']+=1
 if race:publish(B,999)
 result=submit_original(body);TRACE.append({'key':body['key'],'observed_sequence':body['observed_sequence'],'status':result[0],'accepted':result[1].get('accepted'),'pending':len(state.pending),'generation':state.content_generation})
 return result
state.submit=submit;server,thread=page.start_server(state,0);url=state.url+'/'
RESULT.update(server_pid=os.getpid(),port=server.server_address[1]);browser_started=False

def browser(*args,source=None):
 p=subprocess.run(['agent-browser','--session',SESSION,*args],input=source,text=True,capture_output=True,timeout=20)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout.strip()
def js(s):return json.loads(browser('eval','--stdin',source=s))
def wait(fn):
 until=time.monotonic()+5
 while time.monotonic()<until:
  x=fn()
  if x:return x
  time.sleep(.03)
 raise AssertionError('fixture condition timeout')
def prepare(name):
 global race,browser_started
 race=False;counts['keyPOST']=0
 launch=str(uuid.uuid4());nonce=str(uuid.uuid4());d=OUT/name;d.mkdir()
 with state.lock:
  state.stop.clear();state.phase='ready';state.ready=True;state.busy=False;state.error=None;state.steps=0
  state.review_required=False;state.review_confirmation=None;state.review_step=None;state.pending.clear()
  state.frames.clear();state.frame=None;state.content_generation=0;state.launch_request_id=launch;state.launch_status='running'
  state.key_rejections.clear();state.key_rejection_total=state.key_rejection_truncated=0
 publish(A,1);browser('open',url);browser_started=True;browser('set','viewport','1280','1200')
 if 'owned_browser_pids' not in RESULT:
  info=json.loads(browser('session','info','--json'));RESULT['browser_session_info']=info
  rows=[x.split(None,2) for x in subprocess.check_output(['ps','-axo','pid=,ppid=,command='],text=True).splitlines()]
  owned={info['data']['pid']}
  while True:
   extra={int(x[0]) for x in rows if int(x[1]) in owned}-owned
   if not extra:break
   owned|=extra
  RESULT['owned_browser_pids']=sorted(owned)
 wait(lambda:js('!!lastStatus&&frameLoadedFor(lastStatus)&&!document.querySelector(\'.key[data-key="427"]\').disabled'))
 js('window.fixtureClicks=0;document.addEventListener("click",e=>{if(e.target.matches(".key"))window.fixtureClicks++},true);true')
 origin=js('performance.timeOrigin')
 fixture={'completed_step':0,'document_time_origin':origin,'launch_id':launch,'prerequisite_sha256':'f'*64,
          'previous_confirm':None,'historical_observation_sha256':'e'*64,'historical_image_sha256':'d'*64}
 save(d/'fixture-prerequisite-oracle.json',{'scope':'mocked historical review prerequisite, not a visual/semantic pass',**fixture})
 js((OLD/'operator-helpers/deadline.js').read_text()+'('+json.dumps({'expectedURL':url,'expectedLaunchId':launch})+')')
 arm=js('window.__fx3InteractionDeadlineV1.arm('+json.dumps(nonce)+')');assert arm['deadline_ms']==20000
 config={'session':SESSION,'url':url,'launch':launch,'nonce':nonce,'plan_sha':candidate.PLAN_SHA,'step':1,
         'prerequisite_path':d/'fixture-prerequisite-oracle.json','ledger':d/'ledger.json','receipt':d/'receipt.json'}
 return config,fixture,d

def execute(name,expected,mutation='',change=None,loss=False,dynamic=False,server_race=False):
 global race
 c,pr,d=prepare(name);race=server_race
 if change:change(c)
 before=js('({sha:shownSHA,gen:displayedGeneration,seq:displayed})');dynamic_trace=[];stop=threading.Event();dt=None
 if dynamic:
  browser('screenshot',str(d/'historical-fixture.png'))
  def animate():
   started=time.monotonic()
   for i,t in enumerate([.4,.8,2.4,3.2,3.6,4.8,5.2,5.6,6.8,7.2,8.8]):
    if stop.wait(max(0,started+t-time.monotonic())):return
    publish(B if i%2==0 else A,i+2)
    dynamic_trace.append({'elapsed_seconds':time.monotonic()-started,'generation':state.content_generation,'sha256':state.frame['PNG_sha256']})
  dt=threading.Thread(target=animate);dt.start();start=time.monotonic();stop.wait(8.26);elapsed=time.monotonic()-start
 real=candidate.call
 def call(session,args,source=None,timeout=15):
  if args==['eval','--stdin']:
   assert json.loads((d/'ledger.json').read_text())['attempts'][-1]['status']=='reserved_unknown'
   if mutation:source='(()=>{'+mutation+';return '+source+';})()'
   raw=real(session,args,source,timeout)
   if loss:raise subprocess.TimeoutExpired('fixture_lost_reply',12)
   return raw
  return real(session,args,source,timeout)
 try:
  with patch.object(candidate,'prerequisite',return_value=pr),patch.object(candidate,'call',call):r=candidate.click(**c)
 finally:
  stop.set()
  if dt:dt.join()
 assert r['status']==expected,(name,r)
 if js('window.fixtureClicks'):wait(lambda:js('!busy'))
 o={'receipt_status':r['status'],'clicks':js('window.fixtureClicks'),'keyPOST':counts['keyPOST'],'pending':len(state.pending),
    'before_historical_frame':before,'PAGE_attempt':js('fx3KeyAttemptOutcome()'),'server_rejections':state.key_rejection_snapshot()}
 if dynamic:
  o.update(external_wait_seconds=elapsed,dynamic_updates=dynamic_trace)
  save(d/'observation-before-assert.json',o)
  frame=r['result']['snapshot']['click_time_frame'];a=o['PAGE_attempt']
  assert elapsed>=8.26 and frame['content_generation']>before['gen'] and frame['PNG_sha256']==before['sha']
  assert a['frame']==frame and o['clicks']==o['keyPOST']==o['pending']==1
  assert r['scripted_navigation'] is True and r['visual_review_at_click'] is False
  assert 'reviewed' not in r['result']['snapshot']
  o.update(external_wait_seconds=elapsed,dynamic_updates=dynamic_trace,click_time_frame=frame,
           old_static_generation_not_permission=True,ABA_retains_new_generation=True)
 if expected=='preflight_not_clicked':assert o['clicks']==o['keyPOST']==o['pending']==0
 if loss:
  with patch.object(candidate,'prerequisite',return_value=pr):
   try:candidate.click(**{**c,'receipt':d/'forbidden-retry.json'})
   except ValueError as e:assert 'previous click outcome unknown' in str(e)
   else:raise AssertionError('unknown retry permitted')
  assert js('window.fixtureClicks')==1 and counts['keyPOST']==1
 if server_race:
  assert o['clicks']==o['keyPOST']==1 and o['pending']==0
  assert {'sha_mismatch','generation_mismatch'}<=set(o['server_rejections']['records'][-1]['failed_predicates'])
 save(d/'observation.json',o);RESULT['cases'][name]=o
 return c,pr,r

try:
 c,pr,first=execute('dynamic_8_26_second_new_explicit_action','click_invoked',dynamic=True)
 # Simulated guest completion and actual original PAGE capture/confirm protocol;
 # no semantic/menu judgement is inferred from fixture PNGs.
 with state.lock:state.pending.clear();state.steps=1
 state.require_visual_review(1,'visual_changed',True)
 wait(lambda:js('lastStatus?.steps===1&&lastStatus.review_required&&!confirmButton.disabled&&awaitingStep===null'))
 d=OUT/'actual_capture_confirm_and_next_planned_step';d.mkdir();capdir=d/'capture';capdir.mkdir()
 cfg={'url':url,'launch_id':c['launch'],'nonce':c['nonce'],'step':1,'attempt_id':first['result']['attempt_id']}
 before=js((ROOT/'runtime-wrapper/capture_review.js').read_text()+'('+json.dumps(cfg)+')');assert before['status']=='ready_for_screenshot'
 image=capdir/'menu-reference-page.png';browser('screenshot',str(image))
 after=js((ROOT/'runtime-wrapper/capture_after.js').read_text()+'('+json.dumps({**cfg,'before':before['before']})+')');assert after['qualified']
 raw={'status':'qualified_screenshot_for_operator_review','screenshot_path':str(image),'screenshot_file_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'before_eval':before,'after_eval':after}
 save(capdir/'capture-result.json',raw)
 cvspec=importlib.util.spec_from_file_location('actual_capture_validation',ROOT/'runtime-wrapper/capture_validation.py');cv=importlib.util.module_from_spec(cvspec);cvspec.loader.exec_module(cv)
 valid=cv.validate_capture(0,json.dumps(raw),capdir)
 spec2=importlib.util.spec_from_file_location('original_explicit_confirm',OLD/'operator-helpers/explicit_confirm_cli.py');confirm=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(confirm)
 cr=confirm.operate(SESSION,url,c['launch'],c['nonce'],1,valid['firmware_png_sha256'],'scripted fixture protocol approval only; no real visual review',d/'original-confirm-receipt.json')
 assert cr['status']=='confirmed_and_cancelled' and cr['browser_result']['expected']['content_generation']==valid['firmware_generation']
 # A new current frame does not rewrite the exact historical confirmation.
 publish(B,888);wait(lambda:js('frameLoadedFor(lastStatus)&&shownSHA==='+json.dumps(hashlib.sha256(B).hexdigest())))
 new_nonce=str(uuid.uuid4());js('window.__fx3InteractionDeadlineV1.arm('+json.dumps(new_nonce)+')')
 previous={'expected':cr['browser_result']['expected'],'receipt_sha256':hashlib.sha256((d/'original-confirm-receipt.json').read_bytes()).hexdigest(),'attempt_id':first['result']['attempt_id'],'nonce':c['nonce']}
 next_pr={**pr,'completed_step':1,'previous_confirm':previous}
 with patch.object(candidate,'prerequisite',return_value=next_pr):second=candidate.click(**{**c,'nonce':new_nonce,'step':2,'receipt':d/'step2-receipt.json'})
 wait(lambda:js('fx3KeyAttemptOutcome()?.outcome==="accepted"'))
 assert second['status']=='click_invoked' and js('window.fixtureClicks')==counts['keyPOST']==2 and len(state.pending)==1
 assert second['result']['snapshot']['previous_confirm']['expected']['content_generation']==valid['firmware_generation']
 assert second['click_time_frame']['content_generation']!=valid['firmware_generation']
 RESULT['cases']['actual_capture_confirm_next_step']={'status':'passed_protocol_only','two_explicit_calls':True,'total_clicks':2,'total_keyPOST':2,'actual_original_confirm':cr['status'],'historical_confirm_generation':valid['firmware_generation'],'next_click_generation':second['click_time_frame']['content_generation'],'real_visual_semantics':False}
 save(d/'observation.json',RESULT['cases']['actual_capture_confirm_next_step'])
 execute('old_nonce','preflight_not_clicked',change=lambda c:c.update(nonce=str(uuid.uuid4())))
 execute('stopping','preflight_not_clicked',mutation="ending=true;lastStatus.phase='stopping';lastStatus.ready=false")
 execute('invalid_loaded_frame','preflight_not_clicked',mutation='lastStatus.render_valid=false')
 execute('postclick_server_generation_race','click_invoked',server_race=True)
 execute('unknown_reply_no_retry','unknown',loss=True)
 # Actual new helper __main__, no oracle injection: bad plan/step/missing prerequisite all refuse before browser mutation.
 c,pr,d=prepare('host_cli_invalid_inputs')
 def cli(**updates):
  config={**c,**updates};args=['python3','-B',str(ROOT/'operator-helpers/planned_navigation_click.py')]
  for k,v in config.items():args+=['--'+k.replace('_','-'),str(v)]
  p=subprocess.run(args,capture_output=True,text=True,timeout=10)
  assert p.returncode==2 and json.loads(p.stdout)['status']=='host_preflight_refused'
  return {'argv':args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 observations=[cli(plan_sha='0'*64),cli(step=0),cli(step=2,prerequisite_path=d/'no-previous-confirm.json')]
 assert js('window.fixtureClicks')==counts['keyPOST']==0
 save(d/'actual-main-results.json',observations);RESULT['cases']['actual_helper_main_rejections']={'cases':3,'clicks':0,'keyPOST':0}
 RESULT['passed']=True
finally:
 if browser_started:
  try:RESULT['browser_close']=browser('close')
  except BaseException as e:RESULT['browser_close_error']=type(e).__name__
 server.shutdown();server.server_close();thread.join(timeout=2);RESULT['server_thread_alive']=thread.is_alive()
 with socket.socket() as s:RESULT['port_connect_ex_after_close']=s.connect_ex(('127.0.0.1',RESULT['port']))
 RESULT['owned_pid_alive_after']={}
 for pid in RESULT.get('owned_browser_pids',[]):
  try:os.kill(pid,0);alive=True
  except ProcessLookupError:alive=False
  RESULT['owned_pid_alive_after'][str(pid)]=alive
 save(OUT/'server-submit-trace.json',TRACE);save(OUT/'DYNAMIC-RESULT.json',RESULT)
print(json.dumps({'passed':RESULT.get('passed'),'groups':len(RESULT['cases']),'port_closed':RESULT['port_connect_ex_after_close']!=0,'owned_pid_alive_after':RESULT['owned_pid_alive_after']}))
assert RESULT.get('passed') and not RESULT['server_thread_alive'] and RESULT['port_connect_ex_after_close']!=0 and not any(RESULT['owned_pid_alive_after'].values())
