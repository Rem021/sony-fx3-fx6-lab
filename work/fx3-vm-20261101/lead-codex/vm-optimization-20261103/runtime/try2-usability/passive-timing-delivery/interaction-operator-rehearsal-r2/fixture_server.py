#!/usr/bin/env python3
"""One rehearsal fixture: pinned PAGE/TrialState, fake MENU, no guest or QEMU."""
import datetime, hashlib, importlib.util, json, os, signal, threading, time, uuid
from pathlib import Path

HERE=Path(__file__).resolve().parent
DEL=HERE.parent
PAGE=DEL/'v25-r17-tail-receipt/trial_web_v22_navigation_review.py'
RUN=DEL.parent/'runs/v25gate-n64-r17-c33f8c46'
PARTIAL=RUN/'trial-step-01-key-1ab.png'
COMPLETE=RUN/'trial-final.png'
assert hashlib.sha256(PAGE.read_bytes()).hexdigest()=='cfd4239effb34c8be3381eff9c1de3ebf0f6ca4d10af16c86c167e3d76ee82bb'
assert hashlib.sha256(COMPLETE.read_bytes()).hexdigest()=='60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292'
spec=importlib.util.spec_from_file_location('rehearsal_original_r17',PAGE)
page=importlib.util.module_from_spec(spec);spec.loader.exec_module(page)
from dependency_gate import verify
verify() # No fixture process before coordinator dependency release.
loglock=threading.RLock()
def stamp():return {'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host_monotonic':time.monotonic()}
def log(event,**data):
    with loglock:
        with (HERE/'fixture-events.jsonl').open('a') as f:f.write(json.dumps({'event':event,**stamp(),**data},ensure_ascii=False)+'\n')

state=page.TrialState('SIMULATED-operator-rehearsal-r2',600,32)
state.update(phase='awaiting_launch',message='SIMULATED fixture; no guest or VM exists')
shutdown=threading.Event();target_timer=None
def publish(path,seq,label):
    data=path.read_bytes();state.publish(data,{'sequence':seq,'PNG_sha256':hashlib.sha256(data).hexdigest(),'width':960,'height':640,'all_zero_pixels':False})
    log('fixture_publish_'+label,sequence=seq,PNG_sha256=hashlib.sha256(data).hexdigest(),content_generation=state.content_generation,source_path=str(path))
original_submit=state.submit
def fake_menu(body):
    global target_timer
    log('fake_menu_handler_enter',body=body)
    code,reply=original_submit(body)
    if code==202:
        item=state.take();assert item['key']==0x1ab and state.steps==0
        state.update(steps=1)
        state.require_visual_review(1,'visual_pending',True)
        target_timer=threading.Timer(7.0,lambda:publish(COMPLETE,213,'complete'))
        target_timer.start()
        log('fake_menu_scheduled_target',delay_seconds=7.0,scope='specified fixture delay; not measured native latency')
    log('fake_menu_handler_exit',HTTP_status=code,body=reply)
    return code,reply
state.submit=fake_menu
server,server_thread=page.start_server(state,0)
original_reply=server.RequestHandlerClass.reply
def recorded_reply(handler,code,data,kind='application/json; charset=utf-8',extra=None):
    entry=stamp()
    result=original_reply(handler,code,data,kind,extra)
    log('HTTP_reply_written',request_method=handler.command,path=handler.path,HTTP_status=code,
        body=data if handler.command=='POST' else None,reply_enter=entry)
    return result
server.RequestHandlerClass.reply=recorded_reply
config={'scope':'SIMULATED original r17 PAGE/TrialState; no guest/VM',**stamp(),'fixture_pid':os.getpid(),'url':state.url+'/',
        'session':'fx3-deadline-operator-rehearsal-r2-'+uuid.uuid4().hex[:8],'nonce':str(uuid.uuid4()),
        'specified_target_delay_seconds':7.0,'production_deadline_ms':20000,'launch_id':None}
with (HERE/'fixture.json').open('x') as f:json.dump(config,f,indent=2);f.write('\n')
print(json.dumps(config),flush=True)
def sig(signum,frame):log('fixture_shutdown_signal',signal=signum);shutdown.set()
signal.signal(signal.SIGTERM,sig);signal.signal(signal.SIGINT,sig)
try:
    while not shutdown.wait(.02):
        if state.launch_event.is_set() and state.phase=='awaiting_launch':
            state.update(phase='ready',ready=True,launch_status='running',message='SIMULATED fixture ready; no guest exists')
            publish(PARTIAL,212,'partial_initial')
            log('fixture_fake_launch_ready',launch_id=state.launch_request_id)
        if state.stop.is_set() and state.phase=='stopping':
            if target_timer:target_timer.cancel()
            state.update(phase='finished',ready=False,message='SIMULATED fixture ended; no VM lifecycle claim',result={'scope':'simulation_only'})
            log('fixture_finished')
finally:
    if target_timer:target_timer.cancel();target_timer.join(timeout=2)
    server.shutdown();server.server_close();server_thread.join(timeout=2)
    log('fixture_server_closed',server_thread_alive=server_thread.is_alive(),snapshot=state.snapshot(),final_ack_seen=state.final_receipt_seen.is_set())
