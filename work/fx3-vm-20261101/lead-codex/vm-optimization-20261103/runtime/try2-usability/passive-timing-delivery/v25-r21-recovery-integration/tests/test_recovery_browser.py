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
try:
 f=Fixture()
 try:
  f.arm();ledger=OUT/'ledger.json'
  clicked=operator_click(SESSION,f.url,f.launch,f.nonce,427,hashlib.sha256(A).hexdigest(),1,'fixture explicit MENU',ledger,OUT/'first-click.json')
  assert clicked['status']=='click_invoked',clicked
  wait(lambda:ev('fx3KeyAttemptOutcome()?.outcome')=='explicit_rejected_unqueued')
  wait(lambda:ev('!!lastStatus?.ready && shownSHA===lastStatus.frame?.PNG_sha256 && !document.querySelector(\'[data-key="427"]\').disabled'))
  a=ev('fx3KeyAttemptOutcome()');bind={k:a[k] for k in ('attempt_id','document_time_origin','launch_request_id','key','base_step','expected_step')};bind.update(PNG_sha256=a['frame']['PNG_sha256'],content_generation=a['frame']['content_generation'],sequence=a['frame']['sequence'],nonce=a['alarm_nonce'])
  bp=OUT/'binding.json';bp.write_text(json.dumps(bind,indent=2)+'\n')
  review=capture(SESSION,f.url,f.launch,f.nonce,bind,OUT/'review');assert review['status']=='qualified_review_screenshot',review
  assert f.keys==1 and f.confirms==0 and f.state.steps==0
  # The screenshot of B becomes historical when an ordinary valid A frame arrives.
  f.publish(A);wait(lambda:ev('displayedGeneration===lastStatus?.frame?.content_generation && shownSHA===lastStatus?.frame?.PNG_sha256 && shownSHA==='+json.dumps(hashlib.sha256(A).hexdigest())))
  reviewed=json.loads((OUT/'review/review-result.json').read_text())
  basecfg={'url':f.url,'launch_id':f.launch,'nonce':f.nonce,'binding':bind,'review':reviewed,'target':'fixture explicit cleanup'}
  wrong=dict(basecfg);wrong['binding']=dict(bind,attempt_id=str(uuid.uuid4()))
  refusal=ev((OPS/'recovery_cancel.js').read_text()+'('+json.dumps(wrong)+')')
  assert refusal['status']=='refused' and not refusal['cancel_invoked']
  wrong=dict(basecfg,nonce=str(uuid.uuid4()))
  refusal_nonce=ev((OPS/'recovery_cancel.js').read_text()+'('+json.dumps(wrong)+')')
  assert refusal_nonce['status']=='refused' and not refusal_nonce['cancel_invoked']
  tampered=(OPS/'recovery_cancel.js').read_text().replace('f1eb5a54e36b8395a419fee107b87a22fae86dc7eb3c32debfbf6e783e930eab','0'*64)
  refusal_page=ev(tampered+'('+json.dumps(basecfg)+')')
  assert refusal_page['status']=='refused' and not refusal_page['cancel_invoked']
  assert ev('window.__fx3InteractionDeadlineV1.status().current.state')=='armed'
  CASES['wrong_attempt_nonce_PAGE_no_cancel']={'attempt':refusal,'nonce':refusal_nonce,'PAGE':refusal_page}
  result=cancel(SESSION,f.url,f.launch,f.nonce,bind,OUT/'review/review-result.json','operator reviewed unqueued attempt; alarm cleanup only',OUT/'cancel',ledger)
  assert result['status']=='cancelled_unqueued_alarm_only',result
  br=result['browser_result'];assert br['historical_review_not_current'] and br['no_visual_approval'] and br['no_guest_key'] and br['no_confirm_visual'] and not br['server_atomic_permission']
  assert f.keys==1 and f.confirms==0 and f.state.steps==0
  again=ev((OPS/'recovery_cancel.js').read_text()+'('+json.dumps(basecfg)+')');assert again['status']=='refused' and not again['cancel_invoked']
  CASES['old_alarm_cancelled_cannot_repeat']={'result':again}
  CASES['historical_review_B_current_A_cancel_only']={'result':br,'key_posts':f.keys,'confirm_posts':f.confirms,'guest_steps':f.state.steps}
  # A later, separate explicit operator fixture click with a fresh alarm is the only next key.
  f.nonce=str(uuid.uuid4());f.arm()
  current=ev('({sha:shownSHA,gen:displayedGeneration})')
  second=operator_click(SESSION,f.url,f.launch,f.nonce,427,current['sha'],current['gen'],
                        'fixture operator separately reviewed current A',ledger,OUT/'second-click.json')
  assert second['status']=='click_invoked',second
  wait(lambda:f.keys==2);assert f.state.pending and f.state.steps==0
  CASES['separate_explicit_new_click']={'key_posts':f.keys,'confirm_posts':f.confirms,
                                     'pending':len(f.state.pending),'receipt':second}
 finally:f.close()
 g=Fixture()
 try:
  g.arm()
  stale=operator_click(SESSION,g.url,g.launch,g.nonce,427,hashlib.sha256(B).hexdigest(),1,
                       'fixture deliberately stale reviewed image',OUT/'stale-ledger.json',OUT/'stale-click.json')
  assert stale['status']=='unknown' and g.keys==0 and g.confirms==0
  CASES['stale_reviewed_image_refused_zero_key']={'receipt':stale,'key_posts':g.keys}
 finally:g.close()
finally:
 try:browser('close')
 except Exception:pass
(OUT/'RESULT.json').write_text(json.dumps({'passed':True,'scope':'offline Chrome fixture, no VM or real operator semantic review','cases':CASES},ensure_ascii=False,indent=2)+'\n')
print('PASS',len(CASES),OUT)
