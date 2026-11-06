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

    def update(self, **kwargs):
        with self.lock:
            for key, value in kwargs.items():
                setattr(self, key, value)

    def publish(self, png, frame):
        with self.lock:
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
                                  and not self.error and self.render_valid and self.steps < self.max_steps),
                    'busy': self.busy, 'steps': self.steps, 'max_steps': self.max_steps,
                    'render_valid': self.render_valid,
                    'black_after_ready_count': len(self.black_after_ready),
                    'frame': self.frame, 'result': self.result,
                    'remaining_seconds': max(0, int(self.deadline-time.monotonic())),
                    'events': list(self.events[-12:])}

    def submit(self, body):
        with self.lock:
            key, sequence = body.get('key'), body.get('observed_sequence')
            if type(key) is not int or key not in KEYS:
                return 400, {'error': '仅支持页面上的七个按钮。'}
            if type(sequence) is not int or sequence not in self.frames:
                return 409, {'error': '请等待当前画面显示后再按键。'}
            if not self.render_valid or not self.frame or self.frames[sequence]['PNG_sha256'] != self.frame['PNG_sha256']:
                return 409, {'error': '当前画面已变化或不可用，请等待并查看最新画面。'}
            if self.stop.is_set() or self.error or self.phase in ('stopping', 'finished'):
                return 409, {'error': '试用已停止接收按键。'}
            if not self.ready or self.busy or self.pending:
                return 409, {'error': '上一按键仍在处理，请稍候。'}
            if self.steps >= self.max_steps:
                return 409, {'error': '本轮已达配置的按键上限，请结束后重新启动。'}
            item = {'key': key, 'label': KEYS[key], 'observed_frame': self.frames[sequence],
                    'requested_monotonic': time.monotonic(), 'source': 'local_web_user'}
            self.pending.append(item)
            self.busy = True
            return 202, {'accepted': True, 'next_step': self.steps+1, 'key': hex(key)}

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
#status{color:#eee;min-height:3em}#error{color:#ffb0ab;white-space:pre-wrap;overflow-wrap:anywhere}
.small{font-size:13px}#events{padding-left:20px;font-size:13px;color:#bdc2cd}details{margin-top:20px}summary{cursor:pointer;color:#bdc2cd}
</style><h1>FX3 固件菜单试用</h1><p>等待待机画面出现后，按 MENU 打开菜单。首次打开 MENU 可能较慢；每次按键后，请等画面更新再继续。原生省电设置与本轮时间上限分开生效。</p>
<div class="layout"><div class="screen"><span id="placeholder">正在启动固件…</span><img id="frame" alt="固件最新提交画面"></div>
<div class="controls"><div id="status" role="status">正在连接…</div><p id="meta" class="small"></p><div id="error" role="alert"></div>
<div class="pad"><button class="key up" data-key="3" disabled>↑ 上</button><button class="key left" data-key="21" disabled>← 左</button><button class="key" data-key="428" disabled>确定</button><button class="key" data-key="431" disabled>右 →</button><button class="key down" data-key="48" disabled>↓ 下</button></div>
<div class="wide"><button class="key" data-key="427" disabled>MENU</button><button class="key" data-key="504" disabled>删除 / C4</button></div>
<button id="end">结束试用</button><ol id="events"></ol></div></div>
<details open><summary>当前限制</summary><p class="small">当前为实验候选，持续操作仍可能触发原生省电关机，尚未通过完整使用验收。当前固定副本已在冷启动观察到 English；图标与橙色焦点仍需逐屏观察；无实时取景，画面来自软件 OSD 采样，尚未证明原 CP 多画面层合成。每轮默认最多 4096 次按键、最长 60 分钟；以启动参数为准。关闭网页不会结束模拟器，请点击“结束试用”或在启动终端按 Ctrl-C。</p></details>
<script>
const token=__TOKEN__;
let displayed=0,shown=0,shownSHA='',busy=false,ending=false,finished=false;
let lastURL=null,renderFault=null,lastStatus=null,awaitingStep=null,deliveryUnknown=false;
const image=document.querySelector('#frame'),statusEl=document.querySelector('#status');
const err=document.querySelector('#error'),endButton=document.querySelector('#end');
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
function disableKeys(){keys.forEach(b=>b.disabled=true);}
function enableKeys(s){
 const visual=!!s.frame&&displayed>0&&shownSHA===s.frame.PNG_sha256&&s.render_valid&&!renderFault;
 keys.forEach(b=>b.disabled=!s.ready||busy||ending||awaitingStep!==null||!visual);
}
async function showFrame(s){
 if(!s.frame)return;
 if(s.frame.PNG_sha256===shownSHA){displayed=shown=s.frame.sequence;return;}
 const {response,body}=await request('/frame.png',{},'blob');
 const seq=Number(response.headers.get('X-Frame-Sequence')),sha=response.headers.get('X-Frame-PNG-SHA256');
 if(!Number.isSafeInteger(seq)||seq<=0||!sha)throw Error('画面身份缺失');
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
 displayed=shown=seq;shownSHA=sha;
 if(lastURL)URL.revokeObjectURL(lastURL);lastURL=u;
}
async function tick(){
 if(finished)return;
 try{
   const s=(await request('/api/status')).body;lastStatus=s;
   statusEl.textContent=s.message;err.textContent=s.error||'';
   document.querySelector('#meta').textContent=`按键 ${s.steps}/${s.max_steps} · 剩余 ${Math.ceil(s.remaining_seconds/60)} 分钟 · 提交帧 ${s.frame?s.frame.sequence:'等待中'}`;
   document.querySelector('#events').replaceChildren(...s.events.map(e=>{
     const li=document.createElement('li');li.textContent=e;return li;
   }));
   // A final server receipt remains authoritative even if its last image is unavailable.
   if(s.phase==='finished'){
     finished=true;disableKeys();endButton.disabled=true;return;
   }
   if(s.phase==='stopping'){ending=true;disableKeys();}
   if(awaitingStep!==null&&!busy&&!deliveryUnknown&&s.steps>=awaitingStep&&!s.busy){
     awaitingStep=null;deliveryUnknown=false;
   }
   if(deliveryUnknown)err.textContent='按键是否送达尚未确认，已暂停新按键；请结束本轮后重新启动。';
   if(s.frame&&s.frame.sequence!==shown)await showFrame(s);
   renderFault=null;enableKeys(s);
 }catch(e){
   renderFault=e.message;disableKeys();err.textContent=renderFault;
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
   err.textContent='';
 }catch(e){
   if(e.deliveryUnknown===false){awaitingStep=null;deliveryUnknown=false;}
   else{deliveryUnknown=true;}
   err.textContent=e.message;
 }finally{busy=false;}
});
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
                return self.reply(200, data, 'image/png', {'X-Frame-Sequence': str(frame['sequence']), 'X-Frame-PNG-SHA256': frame['PNG_sha256']})
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
            if self.path == '/api/stop':
                state.update(ready=False, phase='stopping', message='正在结束试用并回收资源…')
                state.stop.set()
                return self.reply(202, {'stopping': True})
            return self.reply(404, {'error': '操作不存在。'})

    class Server(ThreadingHTTPServer):
        daemon_threads = True

    server = Server(('127.0.0.1', port), Handler)
    state.url = 'http://127.0.0.1:' + str(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, name='fx3-trial-loopback', daemon=True)
    thread.start()
    return server, thread
