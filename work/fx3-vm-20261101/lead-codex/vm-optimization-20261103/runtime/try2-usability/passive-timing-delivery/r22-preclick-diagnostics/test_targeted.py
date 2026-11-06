"""Offline fixture only: frozen r21 PAGE/TrialState, real owned Chrome, NO VM or human review."""
import hashlib, importlib.util, json, os, socket, struct, subprocess, sys, time, uuid, zlib
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'v25-r21-recovery-integration'
OUT=ROOT/'evidence'
SESSION='fx3-deadline-r22-c83d4bcb5872'
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'operator-helpers'))
import operator_click as candidate
spec=importlib.util.spec_from_file_location('frozen_r21_page',OLD/'trial_web_v22_navigation_review.py')
page=importlib.util.module_from_spec(spec);spec.loader.exec_module(page)

def png(r,g,b):
 def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',2,2,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0'+bytes([r,g,b])*2+b'\0'+bytes([b,r,g])*2))+chunk(b'IEND',b'')
A=png(80,40,20);B=png(20,100,200);SHA=hashlib.sha256(A).hexdigest()
assert candidate.PAGE_SHA==hashlib.sha256(page.PAGE.split('<script>')[1].split('</script>')[0].encode()).hexdigest()
RESULT={'scope':'offline fixture: actual frozen r21 PAGE and server gate; no VM, no human visual review', 'session':SESSION,'cases':{}}
TRACE=[]

def save(name,data):
 (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def browser(*args,source=None):
 p=subprocess.run(['agent-browser','--session',SESSION,*args],input=source,text=True,capture_output=True,timeout=20)
 if p.returncode:raise RuntimeError('fixture browser command failed: '+p.stdout+p.stderr)
 return p.stdout.strip()
def js(source):return json.loads(browser('eval','--stdin',source=source))
def wait(fn):
 until=time.monotonic()+5
 while time.monotonic()<until:
  v=fn()
  if v:return v
  time.sleep(.03)
 raise AssertionError('fixture condition timeout')
def publish(data,seq):
 state.publish(data,{'sequence':seq,'PNG_sha256':hashlib.sha256(data).hexdigest(),'all_zero_pixels':False,'width':2,'height':2})
state=page.TrialState('offline-r22-only',3600,4096)
orig_submit=state.submit
counts={'keyPOST':0}
server_race=False

def submit(body):
 counts['keyPOST']+=1
 if server_race:publish(B,2)
 code,value=orig_submit(body)
 TRACE.append({'kind':'server_submit','key':body.get('key'),'observed_sequence':body.get('observed_sequence'),'status':code,
               'accepted':value.get('accepted'),'enqueued':len(state.pending), 'generation':state.content_generation})
 return code,value
state.submit=submit
server,thread=page.start_server(state,0)
url=state.url+'/'
RESULT.update(server_pid=os.getpid(),port=server.server_address[1])

def prepare(name):
 global server_race
 server_race=False;counts['keyPOST']=0
 launch=str(uuid.uuid4());nonce=str(uuid.uuid4())
 with state.lock:
  state.stop.clear();state.phase='ready';state.ready=True;state.busy=False;state.error=None;state.steps=0
  state.review_required=False;state.review_confirmation=None;state.review_step=None;state.pending.clear()
  state.frames.clear();state.frame=None;state.content_generation=0;state.launch_request_id=launch;state.launch_status='running'
 publish(A,1)
 browser('open',url)
 browser('set','viewport','1280','1200')
 wait(lambda:js('!!lastStatus && frameLoadedFor(lastStatus) && !document.querySelector(\'.key[data-key="427"]\').disabled'))
 # Captures only click events on the fixture's original buttons, never sends input itself.
 js('window.fixtureClicks=0;document.addEventListener("click",e=>{if(e.target.matches(".key"))window.fixtureClicks++},true);true')
 install=js((OLD/'operator-helpers/deadline.js').read_text()+'('+json.dumps({'expectedURL':url,'expectedLaunchId':launch})+')')
 arm=js('window.__fx3InteractionDeadlineV1.arm('+json.dumps(nonce)+')')
 assert install['deadline_ms']==arm['deadline_ms']==20000
 directory=OUT/name;directory.mkdir()
 return launch,nonce,directory

def run_case(name,expected,mutation='',config_change=None,transport=None,expect_failure=None):
 launch,nonce,d=prepare(name)
 config={'session':SESSION,'url':url,'launch':launch,'nonce':nonce,'key':427,'reviewed_sha':SHA,'reviewed_generation':1,
         'target':'scripted fixture only; no human review','ledger':d/'ledger.json','receipt':d/'receipt.json'}
 if config_change:config_change(config)
 real_call=candidate.call
 invoked=[]
 def call(session,args,source=None,timeout=15):
  if args==['eval','--stdin']:
   reservation=json.loads((d/'ledger.json').read_text())['attempts'][-1]
   assert reservation['status']=='reserved_unknown'
   invoked.append(reservation)
   if transport=='before':raise subprocess.TimeoutExpired('fixture_transport_before',12)
   if transport=='null':return 'null'
   if transport=='malformed':
    value=json.loads(real_call(session,args,source='(()=>{lastStatus.busy=true;return '+source+';})()',timeout=timeout))
    del value['checks']['frame_loaded']
    return json.dumps(value)
   if transport=='foreign':
    value=json.loads(real_call(session,args,source='(()=>{lastStatus.busy=true;return '+source+';})()',timeout=timeout))
    value['snapshot']['expected_launch']=str(uuid.uuid4())
    return json.dumps(value)
   wrapped='(()=>{'+mutation+';return '+source+';})()' if mutation else source
   result=real_call(session,args,source=wrapped,timeout=timeout)
   if transport=='after':raise subprocess.TimeoutExpired('fixture_lost_eval_reply',12)
   return result
  return real_call(session,args,source,timeout)
 with patch.object(candidate,'call',call):
  receipt=candidate.click(**config)
 assert receipt['status']==expected,(name,receipt)
 assert len(invoked)==1
 if expect_failure:assert expect_failure in receipt['result']['failed_checks'],receipt
 if expected=='preflight_not_clicked':
  assert receipt['result']['click_called'] is False
  assert js('window.fixtureClicks')==0 and counts['keyPOST']==0
  assert len(state.pending)==0
  assert js('window.__fx3InteractionDeadlineV1.status().current.state')=='armed'
  # Diagnostic refusal ends the attempt; a second call is forbidden by the unchanged budget policy.
  try:candidate.click(**{**config,'receipt':d/'forbidden-second-receipt.json'})
  except ValueError as e:assert 'previous click outcome unknown; End required' in str(e)
  else:raise AssertionError('no-click must not enable retry')
 if js('window.fixtureClicks')>0:wait(lambda:js('!busy'))
 result={'receipt_status':receipt['status'],'clicks':js('window.fixtureClicks'),'keyPOST':counts['keyPOST'],
         'pending':len(state.pending),'PAGE_attempt':js('fx3KeyAttemptOutcome()'),
         'rejections':state.key_rejection_snapshot(),'reserved_before_eval':invoked,
         'ledger_final':json.loads((d/'ledger.json').read_text())}
 # Preserve raw full sanitized candidate receipt and actual PAGE attempt per case.
 save(name+'/observation.json',result)
 RESULT['cases'][name]=result
 return receipt,result

try:
 browser('open',url)
 RESULT['browser_session_info']=json.loads(browser('session','info','--json'))
 process_rows=[line.strip().split(None,2) for line in subprocess.check_output(['ps','-axo','pid=,ppid=,command='],text=True).splitlines()]
 owned={RESULT['browser_session_info']['data']['pid']}
 while True:
  more={int(row[0]) for row in process_rows if len(row)>2 and int(row[1]) in owned}-owned
  if not more:break
  owned|=more
 RESULT['owned_browser_pids']=sorted(owned)
 RESULT['processes_before']=[' '.join(row) for row in process_rows if int(row[0]) in owned]
 run_case('stale_generation','preflight_not_clicked',config_change=lambda c:c.update(reviewed_generation=2),expect_failure='reviewed_generation_matches')
 run_case('stale_SHA','preflight_not_clicked',config_change=lambda c:c.update(reviewed_sha=hashlib.sha256(B).hexdigest()),expect_failure='reviewed_sha_matches')
 run_case('render_not_loaded','preflight_not_clicked',mutation='displayedGeneration=0',expect_failure='frame_loaded')
 run_case('busy_and_review','preflight_not_clicked',mutation='lastStatus.busy=true;lastStatus.review_required=true;busy=true',expect_failure='server_no_review')
 run_case('wrong_nonce','preflight_not_clicked',config_change=lambda c:c.update(nonce=str(uuid.uuid4())),expect_failure='alarm_nonce_matches')
 run_case('expired_due','preflight_not_clicked',mutation='const originalNow=performance.now.bind(performance);Object.defineProperty(performance,"now",{value:()=>originalNow()+21000})',expect_failure='alarm_due_in_future')
 run_case('key_disabled','preflight_not_clicked',mutation='document.querySelector(\'.key[data-key="427"]\').disabled=true',expect_failure='key_enabled')
 run_case('state_changed_during_digest','preflight_not_clicked',mutation='const originalDigest=crypto.subtle.digest.bind(crypto.subtle);crypto.subtle.digest=async(...a)=>{const r=await originalDigest(...a);lastStatus.busy=true;return r}',expect_failure='server_not_busy')
 r,o=run_case('matching_once','click_invoked');assert o['clicks']==o['keyPOST']==o['pending']==1 and o['PAGE_attempt']['outcome']=='accepted'
 # Inject a server generation change only after the PAGE preflight GET, immediately before original submit.
 # The candidate still uses one original click; the unmodified server rejects its now stale observed frame.
 launch,nonce,d=prepare('server_gate_race')
 server_race=True
 r=candidate.click(SESSION,url,launch,nonce,427,SHA,1,'fixture race only',d/'ledger.json',d/'receipt.json')
 wait(lambda:js('fx3KeyAttemptOutcome()?.outcome==="explicit_rejected_unqueued"'))
 o={'receipt_status':r['status'],'clicks':js('window.fixtureClicks'),'keyPOST':counts['keyPOST'],'pending':len(state.pending),
    'PAGE_attempt':js('fx3KeyAttemptOutcome()'),'rejections':state.key_rejection_snapshot()}
 assert r['status']=='click_invoked' and o['clicks']==o['keyPOST']==1 and o['pending']==0
 assert {'sha_mismatch','generation_mismatch'}<=set(o['rejections']['records'][-1]['failed_predicates'])
 save('server_gate_race/observation.json',o);RESULT['cases']['server_gate_race']=o
 r,o=run_case('script_changed_during_digest','unknown',mutation='const originalDigest=crypto.subtle.digest.bind(crypto.subtle);crypto.subtle.digest=async(...a)=>{const r=await originalDigest(...a);document.scripts[0].textContent+="\\n//fixture mutation";return r}')
 assert o['clicks']==o['keyPOST']==0 and r['result']['decision']=='identity_untrusted'
 r,o=run_case('exception_after_click','unknown',mutation='const originalClick=HTMLButtonElement.prototype.click;HTMLButtonElement.prototype.click=function(){originalClick.call(this);if(this.matches(".key"))throw Error("fixture after click") }')
 assert o['clicks']==o['keyPOST']==1
 r,o=run_case('transport_before_eval','unknown',transport='before');assert o['clicks']==o['keyPOST']==0
 r,o=run_case('transport_after_eval','unknown',transport='after');assert o['clicks']==o['keyPOST']==1
 r,o=run_case('nonobject_null_reply','unknown',transport='null');assert o['ledger_final']['attempts'][0]['status']=='unknown'
 r,o=run_case('foreign_receipt_binding','unknown',transport='foreign');assert o['clicks']==o['keyPOST']==0
 r,o=run_case('malformed_missing_check','unknown',transport='malformed');assert o['clicks']==o['keyPOST']==0
 RESULT['passed']=True
finally:
 try:
  RESULT['browser_close']=browser('close')
 except BaseException as e:RESULT['browser_close_error']=type(e).__name__
 server.shutdown();server.server_close();thread.join(timeout=2)
 RESULT['server_thread_alive']=thread.is_alive()
 with socket.socket() as s:RESULT['server_port_connect_ex_after_close']=s.connect_ex(('127.0.0.1',RESULT['port']))
 # Never run a new browser command to probe cleanup: that could relaunch a daemon.
 RESULT['processes_after']=[x for x in subprocess.check_output(['ps','-axo','pid=,ppid=,command='],text=True).splitlines() if SESSION in x]
 RESULT['owned_pid_alive_after']={}
 for pid in RESULT.get('owned_browser_pids',[]):
  try:os.kill(pid,0);alive=True
  except ProcessLookupError:alive=False
  RESULT['owned_pid_alive_after'][str(pid)]=alive
 RESULT['pid_port_lsof_after']=subprocess.run(['lsof','-nP','-iTCP:'+str(RESULT['port'])],capture_output=True,text=True).stdout
 save('server-submit-trace.json',TRACE);save('RESULT.json',RESULT)
print(json.dumps({'passed':RESULT.get('passed'), 'cases':len(RESULT['cases']),
                 'server_thread_alive':RESULT['server_thread_alive'],
                 'port_closed':RESULT['server_port_connect_ex_after_close']!=0,
                 'owned_processes_after':RESULT['processes_after']}))
assert RESULT.get('passed') and not RESULT['server_thread_alive'] and RESULT['server_port_connect_ex_after_close']!=0
