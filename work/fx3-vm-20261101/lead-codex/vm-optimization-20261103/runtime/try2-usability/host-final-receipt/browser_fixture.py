"""Production web module behind a local fault proxy; no QEMU/guest connections."""
import argparse
import hashlib
import http.client
import importlib.util
import json
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
parser = argparse.ArgumentParser()
parser.add_argument('--scenario',choices=('normal','frame-delay','key-ack-drop'),required=True)
args = parser.parse_args()
OUT = HERE/('browser-'+args.scenario)
OUT.mkdir(exist_ok=True)
module_path = PARENT/'trial_web_v5_final_receipt.py'
spec = importlib.util.spec_from_file_location('browser_fixture_web',module_path)
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)
web.PAGE = web.PAGE.replace('<h1>FX3 固件菜单试用</h1>', '<h1>FX3 网页测试：历史画面，无固件输入</h1>')
web.PAGE = web.PAGE.replace('<title>FX3 固件菜单试用</title>', '<title>FX3 宿主网页验收 · '+args.scenario+'</title>')
history = PARENT/'runs/try2mssinternal-a1d8f68a'
images = [next(history.glob('trial-step-01-key-1ab.png')), next(history.glob('trial-step-02-key-1ab.png'))]
pngs = [p.read_bytes() for p in images]
state = web.TrialState('HOST_BROWSER_FIXTURE_NO_GUEST',180,4096)
def publish(index,sequence):
    data = pngs[index]
    state.publish(data,{'sequence':sequence,'PNG_sha256':hashlib.sha256(data).hexdigest(),
                       'pixel_source_sequence':sequence,'all_zero_pixels':False})
publish(0,1)
state.update(phase='ready',ready=True,message='仅测试网页；画面来自历史记录，按键不发往固件。')
backend, backend_thread = web.start_server(state,0)
backend_port = backend.server_address[1]
stop = threading.Event()
requests = []
guard = threading.Lock()
fault_used = False

class Proxy(BaseHTTPRequestHandler):
    def log_message(self,*unused):
        pass

    def relay(self):
        global fault_used
        payload = self.rfile.read(int(self.headers.get('Content-Length','0')))
        with guard:
            row = {'method':self.command,'path':self.path,'monotonic':time.monotonic()}
            requests.append(row)
            fault = None
            if not fault_used and args.scenario=='frame-delay' and self.path=='/frame.png':
                fault = 'frame-body-delay-9-seconds';fault_used = True
            if not fault_used and args.scenario=='key-ack-drop' and self.path=='/api/key':
                fault = 'drop-accepted-key-ack';fault_used = True
            row['fault'] = fault
        conn = http.client.HTTPConnection('127.0.0.1',backend_port,timeout=4)
        try:
            conn.request(self.command,self.path,payload,dict(self.headers))
            response = conn.getresponse()
            body = response.read()
            row['backend_status'] = response.status
            if fault=='drop-accepted-key-ack':
                assert response.status == 202
                self.close_connection = True
                return
            self.send_response(response.status)
            for name,value in response.getheaders():
                if name.lower() not in ('server','date','connection'):
                    self.send_header(name,value)
            self.end_headers()
            if fault=='frame-body-delay-9-seconds':
                self.wfile.flush()
                stop.wait(9)
            self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):
            row['client_disconnected'] = True
        finally:
            conn.close()

    do_GET = relay
    do_POST = relay

class Server(ThreadingHTTPServer):
    daemon_threads = True

proxy = Server(('127.0.0.1',0),Proxy)
state.url = 'http://127.0.0.1:'+str(proxy.server_address[1])
proxy_thread = threading.Thread(target=proxy.serve_forever,daemon=True)
proxy_thread.start()
def interrupted(signum,frame):
    stop.set()
    state.final_receipt_close.set()
signal.signal(signal.SIGINT,interrupted)
signal.signal(signal.SIGTERM,interrupted)
meta = {'scenario':args.scenario,'url':state.url,'scope':'HOST_BROWSER_FIXTURE_NO_GUEST',
        'module_sha256':hashlib.sha256(module_path.read_bytes()).hexdigest(),
        'images':[{'path':str(p),'sha256':hashlib.sha256(data).hexdigest()} for p,data in zip(images,pngs)]}
(OUT/'session.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'url':state.url,'scenario':args.scenario,'fixture_only':True}),flush=True)
delivery = None
try:
    deadline = time.monotonic()+180
    while not stop.is_set() and time.monotonic()<deadline:
        if state.stop.is_set():
            stop.wait(0.3)
            state.update(phase='finished',ready=False,busy=False,
                         message='网页测试已结束；本轮没有启动或操作固件。',
                         result={'fixture_only':True,'guest_started':False})
            delivery = web.wait_for_final_receipt(state)
            break
        item = state.take()
        if item:
            stop.wait(0.2)
            publish(1,state.steps+2)
            with state.lock:
                state.events.append('网页按键已收到；仅切换历史测试画面，未发送固件输入。')
                state.steps += 1
                state.busy = False
                state.message = '测试画面已更新；仍为历史画面。'
        stop.wait(0.05)
finally:
    stop.set()
    proxy.shutdown();proxy.server_close();proxy_thread.join(timeout=2)
    backend.shutdown();backend.server_close();backend_thread.join(timeout=2)
    assert not proxy_thread.is_alive() and not backend_thread.is_alive()
    (OUT/'server-receipt.json').write_text(json.dumps({**meta,'requests':requests,
        'steps':state.steps,'phase':state.phase,'final_delivery':delivery,
        'server_threads_reaped':True,'no_qemu_or_guest_input':True},ensure_ascii=False,indent=2)+'\n')
    print('Fixture servers closed and receipt written',flush=True)
