"""Offline Chrome with actual r21 PAGE/TrialState and derived real deadline; no VM."""
import hashlib,importlib.util,json,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OPS=ROOT/'operator-helpers';OUT=ROOT/'evidence'/('browser-'+uuid.uuid4().hex[:8]);OUT.mkdir(parents=True)
sys.path.insert(0,str(OPS));from recovery_tools import capture,cancel
from operator_click import click as operator_click
spec=importlib.util.spec_from_file_location('r21',ROOT/'trial_web_v22_navigation_review.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
SESSION='fx3-deadline-r21-'+uuid.uuid4().hex[:8];CASES={};A=b'\x89PNG\r\n\x1a\n' # replaced below by known valid fixture PNG
# Use actual helper fixture PNGs already retained; no guest interaction.
BASE=ROOT.parent/'v25-r18-frame-admission/evidence/run-1793830854968'
# Same 12x12 PNG bytes from earlier harness, deterministic.
import struct,zlib
def png(rgb):
 def chunk(k,d):return struct.pack('!I',len(d))+k+d+struct.pack('!I',zlib.crc32(k+d)&0xffffffff)
 row=b'\0'+bytes(rgb)*12
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',12,12,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(row*12))+chunk(b'IEND',b'')
A=png((200,80,20));B=png((30,130,220))
def browser(*args,source=None):
 p=subprocess.run(['agent-browser','--session',SESSION,*args],input=source,text=True,capture_output=True,timeout=20)
 if p.returncode:raise RuntimeError((p.stdout+p.stderr)[-700:])
 return p.stdout.strip()
def ev(s):return json.loads(browser('eval','--stdin',source=s))
def wait(fn,limit=5):
 end=time.monotonic()+limit
 while time.monotonic()<end:
  x=fn()
  if x:return x
  time.sleep(.05)
 raise AssertionError('condition timed out')
class Fixture:
 def __init__(self):
  self.launch=str(uuid.uuid4());self.nonce=str(uuid.uuid4());self.keys=0;self.confirms=0;self.seq=0;self.reject_once=True
  self.state=m.TrialState('r21-offline',3600,4096);self.state.update(phase='ready',ready=True,launch_request_id=self.launch,launch_status='running')
  self.publish(A)
  original=self.state.submit
  def submit(body):
   self.keys+=1
   if self.reject_once:self.reject_once=False;self.publish(B)
   return original(body)
  self.state.submit=submit
  original_confirm=self.state.confirm_visual
  def confirm(body):self.confirms+=1;return original_confirm(body)
  self.state.confirm_visual=confirm
  self.server,self.thread=m.start_server(self.state,0);self.url=self.state.url+'/';browser('open',self.url);browser('set','viewport','1280','1200')
  wait(lambda:ev('!!lastStatus&&lastStatus.ready&&!document.querySelector(\'[data-key="427"]\').disabled'))
 def publish(self,data):
  self.seq+=1;self.state.publish(data,{'sequence':self.seq,'PNG_sha256':hashlib.sha256(data).hexdigest(),'all_zero_pixels':False,'width':12,'height':12})
 def arm(self):
  cfg={'expectedURL':self.url,'expectedLaunchId':self.launch};ev((OPS/'deadline.js').read_text()+'('+json.dumps(cfg)+')')
  h=ev('window.__fx3InteractionDeadlineV1.arm('+json.dumps(self.nonce)+')');assert h['current']['state']=='armed' and h['deadline_ms']==20000
 def click(self):ev('(() => {document.querySelector(\'[data-key="427"]\').click();return true})()')
 def close(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)
def binding(a):
 b={k:a[k] for k in ('attempt_id','document_time_origin','launch_request_id','key','base_step','expected_step')}
 b.update(PNG_sha256=a['frame']['PNG_sha256'],content_generation=a['frame']['content_generation'],sequence=a['frame']['sequence'],nonce=a['alarm_nonce'])
 return b
def config(f):
 a=ev('fx3KeyAttemptOutcome()');b=binding(a)
 review={'status':'qualified_review_screenshot','attempt_id':a['attempt_id'],'nonce':f.nonce,'launch_id':f.launch,'PNG_sha256':hashlib.sha256(A).hexdigest(),'content_generation':1,'screenshot_sha256':'0'*64}
 return {'url':f.url,'launch_id':f.launch,'nonce':f.nonce,'binding':b,'review':review,'target':'fixture only'}
def invoke(c):return ev((OPS/'recovery_cancel.js').read_text()+'('+json.dumps(c)+')')
def cancelled_events():return [x for x in ev('window.__fx3InteractionDeadlineV1.status().events') if x['event']=='cancelled']
try:
 # Local no-POST: ordinary tick loads B during held preflight; then explicit cleanup only.
 f=Fixture()
 try:
  f.arm();ev('''(() => {const orig=window.fetch.bind(window);window.__hold=true;window.fetch=(url,opt)=>{if(window.__hold&&busy&&String(url).includes('/api/status')){window.__hold=false;return new Promise(resolve=>{window.__resume=()=>resolve(orig(url,opt));});}return orig(url,opt);};return true})()''')
  f.click();wait(lambda:ev('!!window.__resume'));f.publish(B)
  wait(lambda:ev('shownSHA===lastStatus?.frame?.PNG_sha256&&displayedGeneration===2'))
  ev('(() => {window.__resume();return true})()');wait(lambda:ev('fx3KeyAttemptOutcome()?.outcome')=='not_posted')
  assert f.keys==0
  c=config(f);c['review']['PNG_sha256']=hashlib.sha256(B).hexdigest();c['review']['content_generation']=2
  x=invoke(c);assert x['status']=='cancelled_unqueued_alarm_only' and len(cancelled_events())==1 and f.keys==f.confirms==0
  CASES['local_no_POST_cancel']={'status':x['status'],'cancel_event':cancelled_events()[0],'key_posts':f.keys,'confirm_posts':f.confirms}
 finally:f.close()
 # Accepted: even with an invented review receipt, cancel JS cannot use this path.
 f=Fixture()
 try:
  f.reject_once=False;f.arm();f.click();wait(lambda:ev('fx3KeyAttemptOutcome()?.outcome')=='accepted')
  x=invoke(config(f));assert x['status']=='refused' and not x['cancel_invoked'] and not cancelled_events()
  CASES['accepted_refused']={'status':x['status'],'key_posts':f.keys,'cancel_count':len(cancelled_events())}
 finally:f.close()
 # In-flight mutation: never cancel before response.
 f=Fixture()
 try:
  f.reject_once=False;orig=f.state.submit
  def delayed(body):time.sleep(1);return orig(body)
  f.state.submit=delayed;f.arm();f.click();wait(lambda:ev('fx3KeyAttemptOutcome()?.outcome')=='post_in_flight')
  x=invoke(config(f));assert x['status']=='refused' and not x['cancel_invoked'] and not cancelled_events()
  CASES['post_in_flight_refused']={'status':x['status'],'cancel_count':len(cancelled_events())}
 finally:f.close()
 # Unknown delivery (503) cannot be interpreted from ready/steps alone.
 f=Fixture()
 try:
  f.arm()
  def unknown(body):f.keys+=1;return 503,{'error':'fixture unknown'}
  f.state.submit=unknown;f.click();wait(lambda:ev('fx3KeyAttemptOutcome()?.outcome')=='delivery_unknown')
  x=invoke(config(f));assert x['status']=='refused' and not x['cancel_invoked'] and not cancelled_events()
  CASES['delivery_unknown_refused']={'status':x['status'],'key_posts':f.keys,'cancel_count':len(cancelled_events())}
 finally:f.close()
 # Natural 20s deadline: no shortened timer or sliding due.
 f=Fixture()
 try:
  f.arm();f.click();wait(lambda:ev('fx3KeyAttemptOutcome()?.outcome')=='explicit_rejected_unqueued')
  c=config(f);armed=ev('window.__fx3InteractionDeadlineV1.status().current')
  wait(lambda:ev('window.__fx3InteractionDeadlineV1.status().current.state')=='expired',limit=22)
  expired=ev('window.__fx3InteractionDeadlineV1.status().current')
  x=invoke(c);assert x['status']=='refused' and not x['cancel_invoked'] and not cancelled_events()
  assert expired['due_ms']==armed['due_ms'] and expired['elapsed_ms']>=20000
  CASES['natural_20s_expired_refused']={'status':x['status'],'armed_due_ms':armed['due_ms'],'expired_due_ms':expired['due_ms'],'elapsed_ms':expired['elapsed_ms'],'cancel_count':len(cancelled_events())}
 finally:f.close()
finally:
 try:browser('close')
 except Exception:pass
(OUT/'RESULT.json').write_text(json.dumps({'passed':True,'scope':'offline real PAGE plus unchanged 20s deadline; no VM','cases':CASES},ensure_ascii=False,indent=2)+'\n')
print('PASS',len(CASES),OUT)
