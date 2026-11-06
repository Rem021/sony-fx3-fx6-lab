"""Loopback-only trial UI. HTTP threads never access QMP, GDB, or guest RAM."""
import collections
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KEYS = {3: '上', 0x30: '下', 0x15: '左', 0x1af: '右',
        0x1ac: '确定', 0x1ab: 'MENU', 0x1f8: '删除 / C4'}


class TrialState:
    def __init__(self, run, max_seconds, max_steps):
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.token = secrets.token_urlsafe(32)
        self.run = str(run)
        self.deadline = time.monotonic() + max_seconds
        self.phase = 'starting'
        self.message = '正在启动固件，请等待待机画面。'
        self.error = None
        self.ready = False
        self.busy = False
        self.visual_state = 'idle'
        self.input_received = False
        self.visual_change_observed = False
        self.review_required = False
        self.review_step = None
        self.review_confirmation = None
        self.browser_ready = False
        self.launch_request_id = None
        self.launch_status = 'awaiting'
        self.launch_event = threading.Event()
        self.content_generation = 0
        self.steps = 0
        self.max_steps = max_steps
        self.render_valid = False
        self.black_after_ready = []
        self.pending = collections.deque()
        self.events = []
        self.png = None
        self.frame = None
        self.frames = collections.OrderedDict()
        self.url = None
        self.result = None
        # Delivery acknowledgement, never a new VM cleanup assertion.
        self.final_receipt_id = secrets.token_urlsafe(16)
        self.final_receipt_seen = threading.Event()
        self.final_receipt_close = threading.Event()

    def update(self, **kwargs):
        with self.lock:
            for key, value in kwargs.items():
                setattr(self, key, value)

    def publish(self, png, frame):
        with self.lock:
            frame = dict(frame)
            if self.frame is None or frame['PNG_sha256'] != self.frame['PNG_sha256']:
                self.content_generation += 1
            frame['content_generation'] = self.content_generation
            if frame.get('all_zero_pixels', False) and self.ready and self.render_valid:
                self.black_after_ready.append({'sequence': frame['sequence'], 'pixel_source_sequence': frame['pixel_source_sequence'], 'host_monotonic': time.monotonic()})
                self.events.append('画面提交了全黑像素；已暂停按键，等待真实画面或结束试用。')
                self.message = '固件提交全黑画面，已暂停按键；可结束试用。'
            self.png, self.frame = png, dict(frame)
            self.render_valid = not frame.get('all_zero_pixels', False)
            self.frames[frame['sequence']] = dict(frame)
            while len(self.frames) > 64:
                self.frames.popitem(last=False)

    def snapshot(self):
        with self.lock:
            return {'phase': self.phase, 'message': self.message, 'error': self.error,
                    'ready': bool(self.ready and not self.busy and not self.stop.is_set()
                                  and not self.error and not self.review_required
                                  and self.render_valid and self.steps < self.max_steps),
                    'busy': self.busy, 'steps': self.steps, 'max_steps': self.max_steps,
                    'visual_state': self.visual_state,
                    'input_received': self.input_received,
                    'visual_change_observed': self.visual_change_observed,
                    'review_required': self.review_required, 'review_step': self.review_step,
                    'review_confirmation': self.review_confirmation,
                    'browser_ready': self.browser_ready, 'launch_request_id': self.launch_request_id,
                    'launch_status': self.launch_status,
                    'render_valid': self.render_valid,
                    'black_after_ready_count': len(self.black_after_ready),
                    'frame': self.frame, 'result': self.result,
                    'final_receipt_id': self.final_receipt_id if self.phase == 'finished' else None,
                    'remaining_seconds': max(0, int(self.deadline-time.monotonic())),
                    'events': list(self.events[-12:])}

    def submit(self, body):
        with self.lock:
            key, sequence = body.get('key'), body.get('observed_sequence')
            if type(key) is not int or key not in KEYS:
                return 400, {'error': '仅支持页面上的七个按钮。'}
            if type(sequence) is not int or sequence not in self.frames:
                return 409, {'error': '请等待当前画面显示后再按键。'}
            if (not self.render_valid or not self.frame
                    or self.frames[sequence]['PNG_sha256'] != self.frame['PNG_sha256']
                    or self.frames[sequence]['content_generation'] != self.content_generation):
                return 409, {'error': '当前画面已变化或不可用，请等待并查看最新画面。'}
            if self.stop.is_set() or self.error or self.phase in ('stopping', 'finished'):
                return 409, {'error': '试用已停止接收按键。'}
            if not self.ready or self.busy or self.pending or self.review_required:
                return 409, {'error': '上一按键仍在处理，请稍候。'}
            if self.steps >= self.max_steps:
                return 409, {'error': '本轮已达配置的按键上限，请结束后重新启动。'}
            item = {'key': key, 'label': KEYS[key], 'observed_frame': self.frames[sequence],
                    'requested_monotonic': time.monotonic(), 'source': 'local_web_user'}
            self.pending.append(item)
            self.busy = True
            return 202, {'accepted': True, 'next_step': self.steps+1, 'key': hex(key)}

    def require_visual_review(self, step, state, changed):
        """Input ACK is known; pixel change alone cannot certify the intended page."""
        with self.lock:
            self.review_required = True
            self.review_step = step
            self.review_confirmation = None
            self.busy = False
            self.visual_state = state
            self.input_received = True
            self.visual_change_observed = changed
            self.message = ('原生按键已接收，画面变化仍须确认；请等完整目标页面出现，'
                            '看清当前画面后点“我已看图，继续”。'
                            if changed else
                            '原生按键已接收，有限观察期内画面未变；请看当前画面，'
                            '确认这是合法无变化操作后再继续。处理完成仍未知。')

    def confirm_visual(self, body):
        """Clear only the host review gate. Never enqueue or write a guest key."""
        with self.lock:
            step, seq, generation, sha, request_id = (
                body.get('step'), body.get('observed_sequence'),
                body.get('content_generation'), body.get('PNG_sha256'), body.get('request_id'))
            if (not isinstance(request_id, str) or not 16 <= len(request_id) <= 80
                    or any(c not in '0123456789abcdef-' for c in request_id)):
                return 400, {'error': '画面确认请求身份无效。'}
            if (self.phase != 'ready' or self.stop.is_set() or self.error or self.busy
                    or self.pending or not self.review_required or step != self.review_step):
                return 409, {'error': '当前没有可确认的按键画面，或原生状态已经变化。'}
            if (type(seq) is not int or type(generation) is not int or not isinstance(sha, str)
                    or seq not in self.frames or not self.frame or not self.render_valid):
                return 409, {'error': '请等待当前有效画面加载完成。'}
            seen = self.frames[seq]
            if (seen['PNG_sha256'] != sha or seen['content_generation'] != generation
                    or self.frame['PNG_sha256'] != sha
                    or self.content_generation != generation or seq > self.frame['sequence']):
                return 409, {'error': '画面身份已过期；请重新查看最新画面后确认。'}
            self.review_required = False
            self.review_step = None
            self.visual_state = 'user_confirmed'
            self.review_confirmation = {'request_id': request_id, 'step': step,
                                        'observed_sequence': seq, 'content_generation': generation,
                                        'PNG_sha256': sha, 'guest_input_written': False}
            self.events.append('%02d · 用户确认已加载的当前画面；没有发送新的固件按键。' % step)
            self.message = '画面已由用户确认；可决定下一键。'
            return 200, {'confirmed': True, **self.review_confirmation}

    def request_stop(self):
        with self.lock:
            # Another tab or delayed request must not undo a terminal receipt.
            if self.phase == 'finished':
                return 200, {'finished': True}
            self.ready = False
            self.phase = 'stopping'
            self.message = '正在结束试用并回收资源…'
            self.stop.set()
            return 202, {'stopping': True}

    def acknowledge_browser_ready(self):
        with self.lock:
            if self.phase != 'awaiting_launch' or self.stop.is_set():
                return 409, {'error':'启动前握手已结束。'}
            self.browser_ready = True
            return 200, {'browser_ready':True}

    def request_launch(self, body):
        with self.lock:
            request_id = body.get('request_id')
            if not isinstance(request_id,str) or len(request_id)!=36 or any(c not in '0123456789abcdef-' for c in request_id):
                return 400, {'error':'启动请求身份无效。'}
            if self.launch_request_id == request_id and not self.stop.is_set() and self.phase not in ('stopping','finished'):
                return 200, {'accepted':True,'request_id':request_id,'guest_spawned_by_http':False}
            if self.launch_request_id or self.phase != 'awaiting_launch' or self.stop.is_set() or not self.browser_ready:
                return 409, {'error':'启动请求已存在、页面未就绪或本轮已结束。'}
            self.launch_request_id = request_id
            self.launch_status = 'accepted'
            self.message = '启动请求已接收；正在检查运行锁。'
            self.launch_event.set()
            return 202, {'accepted':True,'request_id':request_id,'guest_spawned_by_http':False}

    def acknowledge_final(self, body):
        with self.lock:
            if self.phase != 'finished' or body.get('receipt_id') != self.final_receipt_id:
                return 409, {'error': '最终结果尚未生成或回执不匹配。'}
            self.final_receipt_seen.set()
            self.final_receipt_close.set()
            return 200, {'acknowledged': True}

    def take(self):
        with self.lock:
            return self.pending.popleft() if self.pending else None

    def fail(self, reason):
        with self.lock:
            self.error = reason
            self.ready = False
            self.pending.clear()
            self.phase = 'stopping'
            self.message = '检测到异常，已停止接收按键，正在收尾。'
            self.stop.set()


PAGE = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>FX3 固件菜单试用</title>
<style>
:root{color-scheme:dark;font:16px system-ui,-apple-system,sans-serif;background:#15171b;color:#eee}
body{max-width:1080px;margin:28px auto;padding:0 20px}h1{font-size:25px;margin:0 0 8px}
p{line-height:1.6;color:#bdc2cd}.layout{display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap}
.screen{width:min(100%,640px);max-width:640px;flex:1 1 480px;background:#000;border:1px solid #404650;aspect-ratio:4/3;display:grid;place-items:center;position:relative}
img{width:100%;height:100%;object-fit:contain;position:absolute}img:not([src]){display:none}
.controls{min-width:240px;flex:1}.pad{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:20px 0}
button{background:#303743;color:#fff;border:1px solid #566171;border-radius:9px;padding:15px 10px;font:inherit;cursor:pointer;touch-action:manipulation}
button:active{background:#5f738d}button:disabled{opacity:.4;cursor:wait}.up{grid-column:2}.left{grid-column:1}.down{grid-column:2}
.wide{display:flex;gap:10px}.wide button{flex:1}#end{width:100%;margin-top:22px;background:#68383c}
#confirm{width:100%;margin-top:12px;background:#365b48}#review{min-height:2.5em}
#status{color:#eee;min-height:3em}#failure-summary{color:#ffb0ab}#error{color:#ffb0ab;white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}
.small{font-size:13px}#events{padding-left:20px;font-size:13px;color:#bdc2cd}details{margin-top:20px}summary{cursor:pointer;color:#bdc2cd}
</style><h1>FX3 固件菜单试用</h1><p>先确认本机网页可用，再点击“开始本轮模拟器”。待机画面出现后才可按 MENU；每次按键后亲看当前图并确认。原生省电设置与本轮时间上限分开生效。</p>
<div class="layout"><div class="screen"><span id="placeholder">等待您开始本轮…</span><img id="frame" alt="固件最新提交画面"></div>
<div class="controls"><div id="status" role="status">正在连接…</div><p id="meta" class="small"></p><p id="failure-summary" role="alert"></p>
<div class="pad"><button class="key up" data-key="3" disabled>↑ 上</button><button class="key left" data-key="21" disabled>← 左</button><button class="key" data-key="428" disabled>确定</button><button class="key" data-key="431" disabled>右 →</button><button class="key down" data-key="48" disabled>↓ 下</button></div>
<div class="wide"><button class="key" data-key="427" disabled>MENU</button><button class="key" data-key="504" disabled>删除 / C4</button></div>
<p id="review" class="small" role="status"></p><button id="confirm" disabled>我已看清当前完整画面，继续</button>
<button id="start" disabled>开始本轮模拟器</button><button id="end">结束试用</button><ol id="events"></ol></div></div>
<details id="diagnostics" hidden><summary>诊断详情</summary><pre id="error"></pre></details>
<details open><summary>当前限制</summary><p class="small">当前为实验候选，持续操作仍可能触发原生省电关机，尚未通过完整使用验收。当前固定副本已在冷启动观察到 English；图标与橙色焦点仍需逐屏观察；无实时取景，画面来自软件 OSD 采样，尚未证明原 CP 多画面层合成。每轮默认最多 4096 次按键、最长 60 分钟；以启动参数为准。关闭网页不会结束模拟器，请点击“结束试用”或在启动终端按 Ctrl-C。</p></details>
<script>
const token=__TOKEN__;
let displayed=0,shown=0,shownSHA='',displayedGeneration=0,busy=false,ending=false,finished=false;
let lastURL=null,renderFault=null,lastStatus=null,awaitingStep=null,deliveryUnknown=false,reviewAwaiting=false,reviewUnknown=false,pendingConfirm=null;
let explicitRejection=null,uncertainDetail='';
const image=document.querySelector('#frame'),statusEl=document.querySelector('#status');
const err=document.querySelector('#error'),endButton=document.querySelector('#end'),startButton=document.querySelector('#start');
const failureSummary=document.querySelector('#failure-summary'),diagnostics=document.querySelector('#diagnostics');
let launchPending=null,launchUnknown=false,browserReadySent=false;
const confirmButton=document.querySelector('#confirm'),reviewEl=document.querySelector('#review');
const keys=[...document.querySelectorAll('.key')];

// Bound fetch AND body consumption. A lost mutation response is never retried.
async function request(path,options={},bodyKind='json'){
 const controller=new AbortController();let timer;
 const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>{
   const error=new Error('连接超时；操作结果需要重新确认。');
   error.deliveryUnknown=true;reject(error);controller.abort();
 },8000);});
 try{return await Promise.race([deadline,(async()=>{
   const response=await fetch(path,{cache:'no-store',...options,signal:controller.signal});
   if(!response.ok){
     // Only explicit server rejections prove a mutation was rejected.
     const body=await response.json();const error=new Error(body.error||'操作未完成');
     error.deliveryUnknown=response.status>=500;throw error;
   }
   const body=await response[bodyKind]();return {response,body};
 })()]);}finally{clearTimeout(timer);}
}
async function post(path,body){return (await request(path,{method:'POST',
 headers:{'Content-Type':'application/json','X-Trial-Token':token},body:JSON.stringify(body)})).body;}
function disableKeys(){keys.forEach(b=>b.disabled=true);confirmButton.disabled=true;startButton.disabled=true;}
function enableKeys(s){
 const visual=!!s.frame&&displayed>0&&shownSHA===s.frame.PNG_sha256&&
   displayedGeneration===s.frame.content_generation&&s.render_valid&&!renderFault;
 keys.forEach(b=>b.disabled=!s.ready||busy||ending||awaitingStep!==null||deliveryUnknown||reviewAwaiting||reviewUnknown||!visual);
 confirmButton.disabled=!s.review_required||!s.input_received||busy||ending||
   awaitingStep!==null||deliveryUnknown||reviewAwaiting||reviewUnknown||!visual;
}
function confirmationMatches(s,p){
 const c=s.review_confirmation;
 return !!p&&!!c&&s.phase==='ready'&&!s.review_required&&s.steps===p.step&&
   c.request_id===p.request_id&&c.step===p.step&&c.observed_sequence===p.observed_sequence&&
   c.content_generation===p.content_generation&&c.PNG_sha256===p.PNG_sha256&&
   c.guest_input_written===false;
}
function presentFeedback(s){
 // Native failure and terminal state outrank a previous, local 4xx refusal.
 let summary='',detail='';
 if(s.error){
   detail=s.error;
   summary=s.error.startsWith('native_model_power_off_observed')?
     '原生省电关机：本轮已结束，健康检查未通过。':'检测到错误；请展开“诊断详情”查看原始回执。';
 }else if(s.phase==='finished'||s.phase==='stopping'||ending){
   // The authoritative lifecycle message is already in #status.
 }else if(renderFault){
   detail=renderFault;
   summary='网页画面或状态读取失败；本轮暂停新按键，请查看诊断详情。';
 }else if(launchUnknown){
   detail='启动回执未知；只读状态仍未匹配本次请求，请等待或结束本轮。';
   summary='启动请求结果未知，已暂停再次启动；请等待状态确认或结束本轮。';
 }else if(deliveryUnknown||reviewUnknown){
   detail=uncertainDetail;
   summary=deliveryUnknown?
     '按键是否送达尚未确认，已暂停新按键；请结束本轮后重新启动。':
     '画面确认请求结果未知，已暂停新按键；请结束本轮后重新启动。';
 }else if(explicitRejection){
   detail=explicitRejection.detail;
   summary=explicitRejection.kind==='key'?
     '本次按键未被接收。请看最新画面，再由您决定是否重新按键；网页不会自动重发。':
     '本次画面确认未被接收。请看最新画面，再由您决定是否重新确认；网页不会自动确认。';
 }
 diagnostics.hidden=!detail;err.textContent=detail;failureSummary.textContent=summary;
}
async function showFrame(s){
 if(!s.frame)return;
 if(s.frame.PNG_sha256===shownSHA&&s.frame.content_generation===displayedGeneration){displayed=shown=s.frame.sequence;return;}
 const {response,body}=await request('/frame.png',{},'blob');
 const seq=Number(response.headers.get('X-Frame-Sequence')),sha=response.headers.get('X-Frame-PNG-SHA256');
 const generation=Number(response.headers.get('X-Frame-Content-Generation'));
 if(!Number.isSafeInteger(seq)||seq<=0||!sha||!Number.isSafeInteger(generation)||generation<=0)throw Error('画面身份缺失');
 const u=URL.createObjectURL(body);
 try{await new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>settle(Error('画面加载超时，请结束试用或重新连接。')),8000);
   let done=false;
   function settle(error){if(done)return;done=true;clearTimeout(timer);image.onload=image.onerror=null;
     if(error)reject(error);else resolve();}
   image.onload=()=>settle();image.onerror=()=>settle(Error('画面解码失败。'));
   image.src=u;
 });}catch(e){URL.revokeObjectURL(u);throw e;}
 document.querySelector('#placeholder').hidden=true;
 displayed=shown=seq;shownSHA=sha;displayedGeneration=generation;
 if(lastURL)URL.revokeObjectURL(lastURL);lastURL=u;
}
async function tick(){
 if(finished)return;
 try{
   const s=(await request('/api/status')).body;lastStatus=s;
   statusEl.textContent=s.message+(s.visual_state==='visual_pending'?'（输入已接收，仍在观察画面）':'');
   reviewEl.textContent=s.review_required?'原生按键已接收，效果待您看图确认。请只在当前画面完整且符合预期时点继续；无需再按一次固件键。':'';
   document.querySelector('#meta').textContent=s.phase==='finished'?
     `按键 ${s.steps}/${s.max_steps} · 已结束${s.result&&Number.isFinite(s.result.duration_seconds)?` · 实际 ${Math.round(s.result.duration_seconds)} 秒`:''} · 最后提交帧 ${s.frame?s.frame.sequence:'无'}`:
     `按键 ${s.steps}/${s.max_steps} · 剩余 ${Math.ceil(s.remaining_seconds/60)} 分钟 · 提交帧 ${s.frame?s.frame.sequence:'等待中'}`;
   document.querySelector('#events').replaceChildren(...s.events.map(e=>{
     const li=document.createElement('li');li.textContent=e;return li;
   }));
   // A final server receipt remains authoritative even if its last image is unavailable.
   if(s.phase==='finished'){
     if(!s.frame)document.querySelector('#placeholder').textContent='本轮已结束';
     finished=true;disableKeys();endButton.disabled=true;
     presentFeedback(s);
     // Confirm delivery only after displaying the authoritative final status.
     // A lost ACK never overrides that status or initiates another operation.
     if(s.final_receipt_id)void post('/api/final-ack',{receipt_id:s.final_receipt_id}).catch(()=>{});
     return;
   }
   if(s.phase==='stopping'){ending=true;disableKeys();}
   if(s.phase==='awaiting_launch'&&!browserReadySent){
     browserReadySent=true;
     try{await post('/api/browser-ready',{});}catch(e){browserReadySent=false;}
   }
   if(launchPending&&s.launch_request_id===launchPending&&
      ['accepted','starting','running'].includes(s.launch_status)){
     launchUnknown=false;launchPending=null;
   }
   startButton.disabled=s.phase!=='awaiting_launch'||!s.browser_ready||!!s.launch_request_id||
     !!launchPending||launchUnknown||ending||!!renderFault;
   if(launchUnknown){
     // Kept locked until the matching launch request appears in status.
   }
   if(awaitingStep!==null&&!busy&&!deliveryUnknown&&s.steps>=awaitingStep&&!s.busy){
     awaitingStep=null;deliveryUnknown=false;
   }
   if((reviewAwaiting||reviewUnknown)&&confirmationMatches(s,pendingConfirm)){
     reviewAwaiting=false;reviewUnknown=false;pendingConfirm=null;
     if(explicitRejection?.kind==='confirm')explicitRejection=null;
   }
   if(s.frame&&(s.frame.sequence!==shown||s.frame.content_generation!==displayedGeneration))await showFrame(s);
   renderFault=null;enableKeys(s);presentFeedback(s);
 }catch(e){
   renderFault=e.message;disableKeys();err.textContent=renderFault;
   diagnostics.hidden=false;failureSummary.textContent='网页画面或状态读取失败；本轮暂停新按键，请查看诊断详情。';
   if(ending){
     statusEl.textContent='结束状态尚未确认，请查看启动终端；必要时在终端按 Ctrl-C。';
     endButton.disabled=false;
   }
 }finally{if(!finished)setTimeout(tick,400);}
}
keys.forEach(b=>b.onclick=async()=>{
 if(b.disabled||busy||ending||renderFault||awaitingStep!==null||!lastStatus)return;
 busy=true;awaitingStep=lastStatus.steps+1;disableKeys();
 try{
   const ack=await post('/api/key',{key:Number(b.dataset.key),observed_sequence:displayed});
   if(ack.accepted!==true||ack.next_step!==awaitingStep)throw Error('按键回执不完整，请等待状态确认。');
   if(explicitRejection?.kind==='key')explicitRejection=null;
   presentFeedback(lastStatus);
 }catch(e){
   if(e.deliveryUnknown===false){
     awaitingStep=null;deliveryUnknown=false;
     explicitRejection={kind:'key',detail:e.message};
   }else{deliveryUnknown=true;uncertainDetail=e.message;}
   presentFeedback(lastStatus);
 }finally{busy=false;}
});
startButton.onclick=async()=>{
 if(startButton.disabled||!lastStatus||lastStatus.phase!=='awaiting_launch')return;
 const id=crypto.randomUUID().toLowerCase();launchPending=id;startButton.disabled=true;
 try{const ack=await post('/api/start',{request_id:id});
   if(ack.accepted!==true||ack.request_id!==id||ack.guest_spawned_by_http!==false)throw Error('启动回执不完整。');
 }catch(e){if(launchPending===id){
   launchUnknown=true;diagnostics.hidden=false;err.textContent=e.message;
   failureSummary.textContent='启动请求结果未知，已暂停再次启动；请等待状态确认或结束本轮。';
 }}
};
confirmButton.onclick=async()=>{
 if(confirmButton.disabled||!lastStatus||!lastStatus.frame||displayed<=0)return;
 const confirmation={request_id:crypto.randomUUID().toLowerCase(),step:lastStatus.review_step,
   observed_sequence:displayed,content_generation:displayedGeneration,PNG_sha256:shownSHA};
 pendingConfirm=confirmation;
 reviewAwaiting=true;disableKeys();
 try{
   const ack=await post('/api/confirm-visual',confirmation);
   if(ack.confirmed!==true||ack.request_id!==confirmation.request_id||
      ack.step!==confirmation.step||ack.observed_sequence!==confirmation.observed_sequence||
      ack.content_generation!==confirmation.content_generation||
      ack.PNG_sha256!==confirmation.PNG_sha256||ack.guest_input_written!==false)
     throw Error('画面确认回执不完整。');
   // This receipt confirms the historical image only. The next key still needs
   // a fresh, fully loaded frame accepted by enableKeys and the server gate.
   if(pendingConfirm===confirmation){
     reviewAwaiting=false;reviewUnknown=false;pendingConfirm=null;
     if(explicitRejection?.kind==='confirm')explicitRejection=null;
     presentFeedback(lastStatus);
   }
 }catch(e){
   if(pendingConfirm===confirmation){
     if(e.deliveryUnknown===false){
       reviewAwaiting=false;pendingConfirm=null;
       explicitRejection={kind:'confirm',detail:e.message};
     }else{reviewUnknown=true;uncertainDetail=e.message;}
     presentFeedback(lastStatus);
   }
 }
};
endButton.onclick=async()=>{
 if(finished||endButton.disabled)return;
 ending=true;disableKeys();endButton.disabled=true;
 statusEl.textContent='正在结束试用并等待资源回收确认…';
 try{await post('/api/stop',{});}
 catch(e){err.textContent=e.message;endButton.disabled=false;
   statusEl.textContent='结束请求未确认，请查看启动终端；必要时在终端按 Ctrl-C。';}
};
tick();
</script></html>'''


def start_server(state, port):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def valid_host(self):
            return self.headers.get('Host') == state.url.removeprefix('http://')

        def reply(self, code, data, kind='application/json; charset=utf-8', extra=None):
            if isinstance(data, (dict, list)):
                data = json.dumps(data, ensure_ascii=False).encode()
            if isinstance(data, str):
                data = data.encode()
            self.send_response(code)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'")
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, {'error': '仅限本机试用网址。'})
            if self.path == '/':
                return self.reply(200, PAGE.replace('__TOKEN__', json.dumps(state.token)), 'text/html; charset=utf-8')
            if self.path == '/api/status':
                return self.reply(200, state.snapshot())
            if self.path == '/frame.png':
                with state.lock:
                    data, frame = state.png, state.frame
                if data is None:
                    return self.reply(503, {'error': '画面尚未就绪。'})
                return self.reply(200, data, 'image/png', {'X-Frame-Sequence': str(frame['sequence']), 'X-Frame-PNG-SHA256': frame['PNG_sha256'], 'X-Frame-Content-Generation': str(frame['content_generation'])})
            return self.reply(404, {'error': '页面不存在。'})

        def do_POST(self):
            if not self.valid_host() or self.headers.get('X-Trial-Token') != state.token:
                return self.reply(403, {'error': '试用会话无效，请刷新页面。'})
            origin = self.headers.get('Origin')
            if (origin and origin != state.url) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                return self.reply(403, {'error': '仅接受本机试用页面的操作。'})
            try:
                n = int(self.headers.get('Content-Length', '0'))
                if not 0 < n <= 1024 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise ValueError('invalid body')
                body = json.loads(self.rfile.read(n))
                if not isinstance(body, dict):
                    raise ValueError('invalid JSON object')
            except (ValueError, UnicodeError):
                return self.reply(400, {'error': '操作格式无效。'})
            if self.path == '/api/key':
                code, result = state.submit(body)
                return self.reply(code, result)
            if self.path == '/api/browser-ready':
                code, result = state.acknowledge_browser_ready()
                return self.reply(code, result)
            if self.path == '/api/start':
                code, result = state.request_launch(body)
                return self.reply(code, result)
            if self.path == '/api/confirm-visual':
                code, result = state.confirm_visual(body)
                return self.reply(code, result)
            if self.path == '/api/stop':
                code, result = state.request_stop()
                return self.reply(code, result)
            if self.path == '/api/final-ack':
                code, result = state.acknowledge_final(body)
                return self.reply(code, result)
            return self.reply(404, {'error': '操作不存在。'})

    class Server(ThreadingHTTPServer):
        daemon_threads = True

    server = Server(('127.0.0.1', port), Handler)
    state.url = 'http://127.0.0.1:' + str(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, name='fx3-trial-loopback', daemon=True)
    thread.start()
    return server, thread


def wait_for_final_receipt(state, timeout=30.0):
    """Keep final status readable across one bounded 24s browser request cycle.

    Locks and QEMU are already cleaned up by the caller. This wait is bounded
    even if the browser is closed; acknowledgement proves receipt, not success.
    """
    if not 0 <= timeout <= 30:
        raise ValueError('final receipt grace must be within 0..30 seconds')
    with state.lock:
        if state.phase != 'finished':
            raise RuntimeError('cannot acknowledge an unfinished session')
    started = time.monotonic()
    closed = state.final_receipt_close.wait(timeout)
    acknowledged = state.final_receipt_seen.is_set()
    return {'acknowledged': acknowledged, 'wait_seconds': time.monotonic()-started,
            'end_reason': 'browser_ack' if acknowledged else 'local_exit' if closed else 'timeout',
            'maximum_wait_seconds': timeout, 'scope': 'browser_receipt_delivery_only'}
