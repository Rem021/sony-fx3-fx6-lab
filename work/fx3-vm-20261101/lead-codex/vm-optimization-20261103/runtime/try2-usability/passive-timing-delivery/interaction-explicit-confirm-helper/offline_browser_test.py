#!/usr/bin/env python3
"""Real pinned r17 PAGE/TrialState + dedicated Chrome; no VM/guest resource."""
import hashlib,importlib.util,json,struct,subprocess,time,traceback,uuid,zlib
from collections import Counter
from pathlib import Path
from explicit_confirm_cli import operate

HERE=Path(__file__).resolve().parent
DEL=HERE.parent
PAGE_PATH=DEL/'v25-r17-tail-receipt/trial_web_v22_navigation_review.py'
DEADLINE_PATH=DEL/'interaction-deadline-helper/deadline.js'
PINS={PAGE_PATH.name:'cfd4239effb34c8be3381eff9c1de3ebf0f6ca4d10af16c86c167e3d76ee82bb',
      DEADLINE_PATH.name:'93af6b5ce6eb3f736eeed38320c990c6a05701cb6c883493589dadaf4bb57916'}
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(PAGE_PATH.read_bytes())==PINS[PAGE_PATH.name]
assert sha(DEADLINE_PATH.read_bytes())==PINS[DEADLINE_PATH.name]
spec=importlib.util.spec_from_file_location('pinned_r17_page',PAGE_PATH)
page=importlib.util.module_from_spec(spec);spec.loader.exec_module(page)
SESSION='fx3-deadline-explicit-r17'
EVIDENCE=HERE/'evidence'/('run-'+uuid.uuid4().hex[:8])
SOURCE=(HERE/'explicit_confirm.js').read_text()
FAST=SOURCE.replace('performance.now() + 10_000','performance.now() + 800')
assert FAST!=SOURCE and SOURCE.count('performance.now() + 10_000')==1
RESULT={'scope':'host fixture with real r17 PAGE and Chrome; no QEMU',
        'evidence_directory':str(EVIDENCE),
        'page_pin':PINS[PAGE_PATH.name],'deadline_pin':PINS[DEADLINE_PATH.name],
        'explicit_source_sha256':sha(SOURCE.encode()),'cases':{},'cleanup':{}}

def browser(*args,code=None):
    p=subprocess.run(['agent-browser','--session',SESSION,*args],input=code,
                     text=True,capture_output=True,timeout=15)
    if p.returncode:raise AssertionError(f'{args}: {p.stdout} {p.stderr}')
    return p.stdout
def js(code):return json.loads(browser('eval','--stdin',code=code))
def wait(fn,timeout=5):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        v=fn()
        if v:return v
        time.sleep(.04)
    raise AssertionError('fixture wait expired')
def png(rgb):
    def chunk(k,d):return struct.pack('!I',len(d))+k+d+struct.pack('!I',zlib.crc32(k+d)&0xffffffff)
    row=b'\0'+bytes(rgb)*12
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',12,12,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(row*12))+chunk(b'IEND',b'')

class Fixture:
    def __init__(self,name,mode='normal',step=1):
        self.name=name;self.mode=mode;self.step=step;self.counts=Counter();self.server_reply_seen=False
        self.state=page.TrialState('offline-explicit-'+name,3600,4096)
        self.launch=str(uuid.uuid4())
        self.state.update(phase='ready',ready=True,launch_status='running',launch_request_id=self.launch,
                          message='Offline explicit-confirm fixture',steps=step)
        self.a=png((200,80,20));self.b=png((20,80,200));self.publish(self.a,1)
        self.state.require_visual_review(step,'visual_pending',True)
        original=self.state.confirm_visual
        def confirm(body):
            self.counts['confirm']+=1
            if mode=='reject':return 409,{'error':'fixture explicit rejection'}
            if mode=='server_5xx':return 500,{'error':'fixture server failure'}
            if mode=='lost_no_match':time.sleep(9);return 409,{'error':'fixture late rejection'}
            code,reply=original(body)
            if code==200:
                if mode=='advance':self.publish(self.b,2)
                if mode=='aba':self.publish(self.b,2);self.publish(self.a,3)
                if mode=='blocked_after_ack':self.state.update(ready=False)
                if mode=='old_receipt':
                    with self.state.lock:self.state.review_confirmation={**self.state.review_confirmation,'request_id':str(uuid.uuid4())}
                if mode=='lost_recovered':time.sleep(9)
            self.server_reply_seen=True
            return code,reply
        self.state.confirm_visual=confirm
        for method,label in [('submit','key'),('request_stop','stop')]:
            original_method=getattr(self.state,method)
            def wrapped(*a,original_method=original_method,label=label):
                self.counts[label]+=1;return original_method(*a)
            setattr(self.state,method,wrapped)
        self.server,self.thread=page.start_server(self.state,0)
        self.url=self.state.url+'/'
    def publish(self,data,seq):
        self.state.publish(data,{'sequence':seq,'PNG_sha256':sha(data),'all_zero_pixels':False,'width':12,'height':12})
    def open(self,short_alarm=False):
        browser('open',self.url);browser('set','viewport','1280','1200')
        wait(lambda:js('({ok:!!lastStatus&&lastStatus.review_required&&shownSHA===lastStatus.frame?.PNG_sha256&&!confirmButton.disabled})')['ok'])
        script=DEADLINE_PATH.read_text()
        if short_alarm:script=script.replace('const DEADLINE_MS = 20_000;','const DEADLINE_MS = 1_200;')
        h=js(script+'('+json.dumps({'expectedURL':self.url,'expectedLaunchId':self.launch})+')')
        assert h['deadline_ms']==(1200 if short_alarm else 20000)
        self.nonce=str(uuid.uuid4())
        arm=js('window.__fx3InteractionDeadlineV1.arm('+json.dumps(self.nonce)+')')
        assert arm['current']['state']=='armed'
    def invoke(self,label,step=None,png_sha=None,nonce=None,source=None):
        path=EVIDENCE/(self.name+'-'+label+'-receipt.json')
        return operate(SESSION,self.url,self.launch,nonce or self.nonce,step or self.step,
                       png_sha or sha(self.a),'MENU完整菜单已由操作员看清',path,source=source)
    def save(self,label,result):
        shot=EVIDENCE/(self.name+'-'+label+'.png');browser('screenshot','--full',str(shot))
        dom=js('({phase:lastStatus.phase,steps:lastStatus.steps,shownSHA,displayedGeneration,reviewAwaiting,reviewUnknown,pendingConfirm,reviewConfirmation:lastStatus.review_confirmation,ready:lastStatus.ready,renderValid:lastStatus.render_valid,keyDisabled:keys.map(b=>b.disabled),alarm:window.__fx3InteractionDeadlineV1.status()})')
        RESULT['cases'][self.name+'-'+label]={'result':result,'counts':dict(self.counts),'dom':dom,
            'screenshot':shot.name,'screenshot_sha256':sha(shot.read_bytes()),'server_reply_seen':self.server_reply_seen}
    def close(self):
        # Fixture cleanup only: destroy this dedicated document, never touch a user tab.
        try:browser('close')
        except Exception:pass
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)
        assert not self.thread.is_alive()

def case_basic():
    f=Fixture('basic')
    try:
        f.open()
        for label,kw in [('wrong-step',{'step':2}),('wrong-sha',{'png_sha':'0'*64}),
                         ('wrong-nonce',{'nonce':str(uuid.uuid4())})]:
            r=f.invoke(label,**kw);assert r['status']=='refused' and f.counts['confirm']==0
            assert js('window.__fx3InteractionDeadlineV1.status().current.state')=='armed'
            f.save(label,r)
        r=f.invoke('success');assert r['status']=='confirmed_and_cancelled',r
        assert f.counts['confirm']==1 and f.counts['key']==f.counts['stop']==0
        assert r['browser_result']['cancelled']['current']['due_ms']==r['browser_result']['events'][1]['due_ms']
        f.save('success',r)
    finally:f.close()

def case_mode(name,mode,expected,fast=False):
    f=Fixture(name,mode)
    try:
        f.open();r=f.invoke('attempt',source=FAST if fast else SOURCE)
        assert r['status']==expected,(name,r)
        assert f.counts['confirm']==1 and f.counts['key']==0
        alarm=js('window.__fx3InteractionDeadlineV1.status()')
        assert alarm['current']['state']==('cancelled' if expected=='confirmed_and_cancelled' else 'armed')
        f.save('attempt',r)
    finally:f.close()

def case_expired():
    f=Fixture('expired')
    try:
        f.open(short_alarm=True);time.sleep(1.3)
        short=SOURCE.replace('const DEADLINE_MS = 20_000;','const DEADLINE_MS = 1_200;')
        r=f.invoke('refused',source=short)
        assert r['status']=='refused' and f.counts['confirm']==0
        f.save('refused',r)
    finally:f.close()

if __name__=='__main__':
    EVIDENCE.mkdir(exist_ok=True)
    try:
        case_basic()
        case_mode('advance','advance','confirmed_and_cancelled')
        case_mode('aba','aba','confirmed_and_cancelled')
        case_mode('reject','reject','unknown',fast=True)
        case_mode('server-5xx','server_5xx','unknown',fast=True)
        case_mode('old-receipt','old_receipt','unknown',fast=True)
        case_mode('blocked','blocked_after_ack','unknown',fast=True)
        case_mode('lost-no-match','lost_no_match','unknown',fast=True)
        case_mode('lost-recovered','lost_recovered','confirmed_and_cancelled')
        case_expired()
        RESULT['passed']=True
    except BaseException:
        RESULT['passed']=False;RESULT['error']=traceback.format_exc();raise
    finally:
        RESULT['source_sha256_after']=sha((HERE/'explicit_confirm.js').read_bytes())
        RESULT['page_sha256_after']=sha(PAGE_PATH.read_bytes())
        RESULT['deadline_sha256_after']=sha(DEADLINE_PATH.read_bytes())
        (EVIDENCE/'RESULT.json').write_text(json.dumps(RESULT,ensure_ascii=False,indent=2)+'\n')
