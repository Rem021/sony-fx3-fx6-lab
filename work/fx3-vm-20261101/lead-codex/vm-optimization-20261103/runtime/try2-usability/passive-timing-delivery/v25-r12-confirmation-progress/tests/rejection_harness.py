"""Offline browser fixture using the real TrialState and PAGE; never starts QEMU."""
import argparse
import hashlib
import importlib.util
import json
import struct
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def png(rgb):
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    row = b'\0' + bytes(rgb) * 12
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 12, 12, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(row * 12)) + chunk(b'IEND', b''))


parser = argparse.ArgumentParser()
parser.add_argument('--module', type=Path, required=True)
parser.add_argument('--ready-file', type=Path, required=True)
args = parser.parse_args()
spec = importlib.util.spec_from_file_location('trial_fixture_module', args.module)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
state = module.TrialState('offline-browser-fixture', 3600, 4096)
colors = {'A': png((200, 80, 20)), 'B': png((30, 130, 220)), 'BAD': b'not a PNG'}
fixture_lock = threading.RLock()
fixture = {'mode': 'normal', 'requests': {'key': 0, 'confirm': 0}, 'enqueued': 0,
           'seq': 0, 'last_confirmation': None, 'previous_confirmation': None,
           'key_bodies': [], 'confirm_bodies': [], 'delayed_ack_sent': []}


def publish(color):
    with fixture_lock:
        fixture['seq'] += 1
        seq = fixture['seq']
    data = colors[color]
    state.publish(data, {'sequence': seq, 'PNG_sha256': hashlib.sha256(data).hexdigest(),
                         'all_zero_pixels': False, 'width': 12, 'height': 12})


def reset():
    with state.lock, fixture_lock:
        state.phase = 'ready'
        state.message = '离线测试待机画面。'
        state.error = None
        state.ready = True
        state.busy = False
        state.visual_state = 'idle'
        state.input_received = False
        state.visual_change_observed = False
        state.review_required = False
        state.review_step = None
        state.review_confirmation = None
        state.content_generation = 0
        state.steps = 0
        state.pending.clear()
        state.events.clear()
        state.frames.clear()
        state.frame = None
        state.png = None
        state.stop.clear()
        fixture.update(mode='normal', requests={'key': 0, 'confirm': 0}, enqueued=0,
                       seq=0, last_confirmation=None, previous_confirmation=None,
                       key_bodies=[], confirm_bodies=[], delayed_ack_sent=[])
    publish('A')


original_submit = state.submit
original_confirm = state.confirm_visual


def injected_submit(body):
    with fixture_lock:
        fixture['requests']['key'] += 1
        fixture['key_bodies'].append(dict(body))
        mode = fixture['mode']
        fixture['mode'] = 'normal'
    if mode == 'stale_sha':
        publish('B')
    elif mode == 'aba_generation':
        publish('B')
        publish('A')
    elif mode == 'http500':
        return 503, {'error': '离线模拟服务错误。'}
    elif mode == 'invalid_json':
        return 202, 'not valid JSON'
    elif mode == 'timeout':
        time.sleep(9)
        return 503, {'error': '离线模拟超时。'}
    elif mode == 'delayed_409':
        time.sleep(1)
        return 409, {'error': '离线模拟明确拒绝。'}
    code, body = original_submit(body)
    if code == 202:
        with fixture_lock:
            fixture['enqueued'] += 1
        with state.lock:
            state.pending.clear()
            state.steps += 1
            step = state.steps
        state.require_visual_review(step, 'visual_pending', True)
    return code, body


def injected_confirm(body):
    with fixture_lock:
        fixture['requests']['confirm'] += 1
        fixture['confirm_bodies'].append(dict(body))
        mode = fixture['mode']
        fixture['mode'] = 'normal'
    if mode == 'confirm_stale':
        # Force a different SHA regardless of the preceding key-rejection color.
        publish('A' if state.frame['PNG_sha256'] == hashlib.sha256(colors['B']).hexdigest() else 'B')
    elif mode == 'confirm_500':
        return 503, {'error': '离线模拟确认服务错误。'}
    elif mode == 'confirm_response_lost':
        original_confirm(body)
        time.sleep(9)
        return 503, {'error': '离线模拟确认响应丢失。'}
    elif mode in ('confirm_then_b', 'confirm_then_aba', 'confirm_lost_then_b',
                  'confirm_delayed_ack_then_b'):
        code, result = original_confirm(body)
        if code == 200:
            with fixture_lock:
                fixture['previous_confirmation'] = fixture['last_confirmation']
                fixture['last_confirmation'] = dict(state.review_confirmation)
            publish('B')
            if mode == 'confirm_then_aba':
                publish('A')
            if mode == 'confirm_lost_then_b':
                with state.lock:
                    state.review_confirmation = dict(state.review_confirmation, request_id='00000000-wrong')
                time.sleep(9)
                return 503, {'error': '离线模拟确认响应丢失。'}
            if mode == 'confirm_delayed_ack_then_b':
                time.sleep(6)
                with fixture_lock:
                    fixture['delayed_ack_sent'].append(result['request_id'])
        return code, result
    return original_confirm(body)


state.submit = injected_submit
state.confirm_visual = injected_confirm
reset()
web, web_thread = module.start_server(state, 0)


class Control(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send_json(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path != '/stats':
            return self.send_json({'error': 'unknown'})
        with fixture_lock:
            return self.send_json({'requests': dict(fixture['requests']), 'enqueued': fixture['enqueued'],
                                   'mode': fixture['mode'], 'seq': fixture['seq'],
                                   'key_bodies': list(fixture['key_bodies']),
                                   'confirm_bodies': list(fixture['confirm_bodies']),
                                   'delayed_ack_sent': list(fixture['delayed_ack_sent']),
                                   'steps': state.steps, 'review_required': state.review_required,
                                   'content_generation': state.content_generation,
                                   'frame_sequence': state.frame['sequence'] if state.frame else None,
                                   'review_confirmation': state.review_confirmation})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))))
        if self.path == '/reset':
            reset()
        elif self.path == '/mode':
            with fixture_lock:
                fixture['mode'] = body['mode']
        elif self.path == '/publish':
            publish(body['color'])
        elif self.path == '/terminal':
            with state.lock:
                state.error = body.get('error')
                state.phase = body.get('phase', 'finished')
                state.ready = False
                state.message = body.get('message', '离线测试终态。')
        elif self.path == '/tamper-confirmation':
            with state.lock, fixture_lock:
                state.review_confirmation = dict(fixture['last_confirmation'] or {}, **body)
        elif self.path == '/restore-confirmation':
            with state.lock, fixture_lock:
                state.review_confirmation = dict(fixture['last_confirmation'])
        elif self.path == '/previous-confirmation':
            with state.lock, fixture_lock:
                state.review_confirmation = dict(fixture['previous_confirmation'])
        else:
            return self.send_json({'error': 'unknown'})
        return self.send_json({'ok': True})


control = ThreadingHTTPServer(('127.0.0.1', 0), Control)
args.ready_file.write_text(json.dumps({'web': state.url, 'control': 'http://127.0.0.1:' + str(control.server_address[1])}) + '\n')
print(args.ready_file.read_text(), flush=True)
try:
    control.serve_forever()
finally:
    control.server_close()
    web.shutdown()
    web.server_close()
