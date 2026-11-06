"""Controlled backend; untouched r21 PAGE + TrialState; never creates VM/guest."""
import importlib.util,io,signal,sys,uuid
from common import *
from dependency_gate import verify
verify('DEPENDENCY-SERVER-START.json')
spec=importlib.util.spec_from_file_location('r21_original_page',FROZEN/'trial_web_v22_navigation_review.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
state=m.TrialState('OFFLINE-FIXTURE-independent-operator-r21',600,8)
state.update(phase='awaiting_launch',message='OFFLINE FIXTURE; no guest/VM exists')
loglock=threading.RLock();shutdown=threading.Event();calls=0
hist=Path(CFG['historical_root'])
def log(stage,**kw):
 with loglock:
  with (HERE/'fixture-events.jsonl').open('a') as f:f.write(json.dumps({'stage':stage,**stamp(),**kw},ensure_ascii=False)+'\n')
def publish(filename,seq):
 p=hist/filename;data=p.read_bytes()
 # Original publish only; no direct frontend attempt/alarm manipulation.
 state.publish(data,{'sequence':seq,'PNG_sha256':sha(p),'width':640,'height':480,'all_zero_pixels':False})
 log('historical_fixture_publish',source_path=str(p),source_sha256=sha(p),frame=state.frame)
original_submit=state.submit
def controlled_submit(body):
 global calls
 # Acquire the exact original RLock before the induced generation change, and
 # retain it while original_submit re-enters it and fully decides admission.
 with state.lock:
  calls+=1;before=state.snapshot()
  log('submit_enter_under_original_lock',ordinal=calls,request=body,before=before)
  if calls==1:publish('trial-step-01-key-1ab.png',212)
  code,reply=original_submit(body)
  log('original_submit_return_under_same_lock',ordinal=calls,HTTP_status=code,response=reply,pending_count=len(state.pending),steps=state.steps,rejections=state.key_rejection_snapshot())
  if code==202:
   assert calls==2 and len(state.pending)==1 and state.steps==0
   item=state.take();assert item['key']==427
   log('fixture_dequeued_one_accepted_key',item=item,actual_guest_inputs=0)
   state.update(steps=1)
   state.require_visual_review(1,'visual_pending',True)
   publish('trial-final.png',213)
   state.update(message='OFFLINE FIXTURE: historical complete Setup > Area/Date PNG; no guest executes')
  return code,reply
state.submit=controlled_submit
server,server_thread=m.start_server(state,0)
handler=server.RequestHandlerClass;original_post=handler.do_POST;original_reply=handler.reply
# Capture exact HTTP request body through the real handler; exclude token header.
def record_post(h):
 n=int(h.headers.get('Content-Length','0'));raw=h.rfile.read(n);previous=h.rfile
 h._request_log_id=str(uuid.uuid4());h.rfile=io.BytesIO(raw)
 log('HTTP_request',id=h._request_log_id,method=h.command,path=h.path,body_utf8=raw.decode(),headers={k:h.headers.get(k) for k in ('Host','Origin','Content-Type','Sec-Fetch-Site')})
 try:return original_post(h)
 finally:h.rfile=previous

def record_reply(h,code,data,kind='application/json; charset=utf-8',extra=None):
 entry=stamp();result=original_reply(h,code,data,kind,extra)
 log('HTTP_response_written',id=getattr(h,'_request_log_id',None),method=h.command,path=h.path,HTTP_status=code,response=data if isinstance(data,(dict,list)) else None,payload_sha256=hashlib.sha256(data).hexdigest() if kind=='image/png' else None,extra=extra,reply_enter=entry)
 return result
handler.do_POST=record_post;handler.reply=record_reply
config={'scope':'offline original r21 PAGE/TrialState; controlled backend; no VM/guest','pid':os.getpid(),'url':state.url+'/','launch_id':None,'session':CFG['session'],**stamp()};write('fixture.json',config)
print(json.dumps(config),flush=True)
def end_signal(s,f):log('shutdown_signal',signal=s);shutdown.set()
signal.signal(signal.SIGTERM,end_signal);signal.signal(signal.SIGINT,end_signal)
try:
 while not shutdown.wait(.01):
  if state.launch_event.is_set() and state.phase=='awaiting_launch':
   state.update(phase='ready',ready=True,launch_status='running',message='OFFLINE FIXTURE ready; historical standby PNG')
   publish('trial-standby-ready.png',211)
   config['launch_id']=state.launch_request_id;write('fixture.json',config)
   log('fixture_ready',launch_id=state.launch_request_id)
  if state.stop.is_set() and state.phase=='stopping':
   state.update(phase='finished',ready=False,message='OFFLINE FIXTURE ended; no VM lifecycle claim',result={'scope':'offline simulation only','actual_guest_inputs':0})
   log('fixture_finished',snapshot=state.snapshot())
finally:
 server.shutdown();server.server_close();server_thread.join(timeout=2)
 write('fixture-closed.json',{'server_thread_alive':server_thread.is_alive(),'final_ack_seen':state.final_receipt_seen.is_set(),'snapshot':state.snapshot(),'key_rejections':state.key_rejection_snapshot(),'key_calls':calls,'actual_guest_inputs':0,**stamp()})
 log('fixture_closed')
