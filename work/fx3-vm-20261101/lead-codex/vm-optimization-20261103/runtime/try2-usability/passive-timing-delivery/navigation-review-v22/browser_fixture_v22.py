#!/usr/bin/env python3
"""Real browser fixture; historical PNGs, zero QEMU/guest input."""
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
RUN = HERE.parents[1] / 'runs/try2passivetiming-internal-v21-2383af57'
ap = argparse.ArgumentParser()
ap.add_argument('--scenario', choices=('normal', 'key-ack-drop', 'confirm-ack-drop'), required=True)
args = ap.parse_args()
OUT = HERE / ('browser-v22-receipt-' + args.scenario)
OUT.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location('fixture_web', HERE/'trial_web_v22_navigation_review.py')
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)
web.PAGE = web.PAGE.replace('FX3 固件菜单试用', 'FX3 宿主网页测试：历史画面，无固件输入')
names = ['internal-observe-01', 'trial-step-01-key-1ab',
         'internal-observe-02', 'trial-step-02-key-015', 'internal-observe-03']
history = []
for name in names:
    png = (RUN/(name+'.png')).read_bytes()
    frame = json.loads((RUN/(name+'.json')).read_text())
    assert hashlib.sha256(png).hexdigest() == frame['PNG_sha256']
    history.append((png, frame))
state = web.TrialState('HOST_BROWSER_FIXTURE_NO_GUEST', 180, 4096)
state.publish(*history[0])
state.update(phase='ready', ready=True,
             message='仅测试网页；当前是历史 NO CARD 画面，按键不会发给固件。')
backend, backend_thread = web.start_server(state, 0)
backend_port = backend.server_address[1]
stop = threading.Event()
requests = []
guard = threading.Lock()
fault_used = False

class Proxy(BaseHTTPRequestHandler):
    def log_message(self, *unused):
        pass

    def relay(self):
        global fault_used
        payload = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        with guard:
            row = {'method':self.command, 'path':self.path, 'host_monotonic':time.monotonic()}
            requests.append(row)
            fault = None
            if not fault_used and args.scenario == 'key-ack-drop' and self.path == '/api/key':
                fault = 'drop-accepted-key-ack'
                fault_used = True
            if not fault_used and args.scenario == 'confirm-ack-drop' and self.path == '/api/confirm-visual':
                fault = 'drop-accepted-confirmation-ack'
                fault_used = True
            row['fault'] = fault
        conn = http.client.HTTPConnection('127.0.0.1', backend_port, timeout=5)
        try:
            conn.request(self.command, self.path, payload, dict(self.headers))
            response = conn.getresponse()
            body = response.read()
            row['backend_status'] = response.status
            if fault:
                assert response.status == (200 if fault == 'drop-accepted-confirmation-ack' else 202)
                self.close_connection = True
                return
            self.send_response(response.status)
            for name, value in response.getheaders():
                if name.lower() not in ('server', 'date', 'connection'):
                    self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            row['client_disconnected'] = True
        finally:
            conn.close()

    do_GET = relay
    do_POST = relay

class Server(ThreadingHTTPServer):
    daemon_threads = True

proxy = Server(('127.0.0.1', 0), Proxy)
state.url = 'http://127.0.0.1:' + str(proxy.server_address[1])
proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
proxy_thread.start()

def interrupted(signum, frame):
    stop.set()
    state.final_receipt_close.set()

signal.signal(signal.SIGINT, interrupted)
signal.signal(signal.SIGTERM, interrupted)
meta = {'scenario':args.scenario, 'url':state.url,
        'scope':'HOST_BROWSER_FIXTURE_NO_GUEST',
        'module_sha256':hashlib.sha256((HERE/'trial_web_v22_navigation_review.py').read_bytes()).hexdigest(),
        'images':[{'name':name, 'sha256':frame['PNG_sha256']} for name, (_,frame) in zip(names,history)]}
(OUT/'session.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'url':state.url,'scenario':args.scenario,'fixture_only':True}),flush=True)
delivery = None
stage = 0
try:
    deadline = time.monotonic()+180
    while not stop.is_set() and time.monotonic()<deadline:
        if state.stop.is_set():
            stop.wait(0.2)
            state.update(phase='finished', ready=False, busy=False,
                         message='网页测试已结束；没有启动或操作固件。',
                         result={'fixture_only':True,'guest_started':False})
            delivery = web.wait_for_final_receipt(state)
            break
        item = state.take()
        if item:
            stop.wait(0.2)
            if stage == 0 and item['key'] == 0x1ab:
                state.publish(*history[1])
                state.update(steps=1)
                state.require_visual_review(1, 'visual_changed', True)
                stage = 1
            elif stage == 2 and item['key'] == 0x15:
                state.publish(*history[3])
                state.update(steps=2)
                state.require_visual_review(2, 'visual_changed', True)
                stage = 3
            else:
                raise RuntimeError('Fixture accepted unexpected key or stage')
        if stage == 1 and (OUT/'ADVANCE_MENU_FULL').is_file():
            state.publish(*history[2]); stage = 2
        if stage == 3 and (OUT/'ADVANCE_CATEGORY_FULL').is_file():
            state.publish(*history[4]); stage = 4
        stop.wait(0.05)
finally:
    stop.set()
    proxy.shutdown(); proxy.server_close(); proxy_thread.join(timeout=2)
    backend.shutdown(); backend.server_close(); backend_thread.join(timeout=2)
    (OUT/'server-receipt.json').write_text(json.dumps({**meta,'requests':requests,
        'stage':stage,'steps':state.steps,'phase':state.phase,'final_delivery':delivery,
        'confirmation_receipt':state.review_confirmation,
        'key_post_count':sum(r['path']=='/api/key' for r in requests),
        'confirm_post_count':sum(r['path']=='/api/confirm-visual' for r in requests),
        'server_threads_reaped':not proxy_thread.is_alive() and not backend_thread.is_alive(),
        'no_qemu_or_guest_input':True},ensure_ascii=False,indent=2)+'\n')
    print('Fixture servers closed and receipt written',flush=True)
