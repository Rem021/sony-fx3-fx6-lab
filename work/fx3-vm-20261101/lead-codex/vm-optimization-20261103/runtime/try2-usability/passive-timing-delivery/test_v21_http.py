#!/usr/bin/env python3
"""Exercise exact v21 loopback HTTP and final receipt, with no guest."""
from pathlib import Path
import base64
import hashlib
import json
import threading
import time
import urllib.error
import urllib.request
import trial_web_v21_final_timing as web

HERE = Path(__file__).resolve().parent
png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWZkAAAAASUVORK5CYII=')
sha = hashlib.sha256(png).hexdigest()
state = web.TrialState('HOST_FIXTURE_NO_GUEST', 60, 4096)
state.publish(png, {'sequence': 1, 'PNG_sha256': sha, 'pixel_source_sequence': 1, 'all_zero_pixels': False})
state.update(phase='ready', ready=True, visual_state='visual_pending', input_received=True)
server, thread = web.start_server(state, 0)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
checks = []

def get(path):
    with opener.open(state.url + path, timeout=3) as response:
        return response.status, response.headers, response.read()

def post(path, payload, token=True):
    headers = {'Content-Type': 'application/json', 'Origin': state.url}
    if token:
        headers['X-Trial-Token'] = state.token
    request = urllib.request.Request(state.url + path, json.dumps(payload).encode(), headers)
    try:
        response = opener.open(request, timeout=3)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, json.loads(response.read())

try:
    code, _, page = get('/')
    assert code == 200 and b'AbortController' in page and b'final-ack' in page
    checks.append('actual v21 page contains bounded request and final ACK client')
    status = json.loads(get('/api/status')[2])
    assert status['visual_state'] == 'visual_pending' and status['input_received'] is True
    assert status['final_receipt_id'] is None
    checks.append('five-state fields exposed while final receipt remains hidden before finish')
    _, headers, body = get('/frame.png')
    assert body == png and headers['X-Frame-PNG-SHA256'] == sha
    checks.append('immutable PNG bytes and identity header agree')
    assert post('/api/key', {'key': 427, 'observed_sequence': 1}, token=False)[0] == 403
    assert post('/api/key', {'key': 427, 'observed_sequence': 1})[0] == 202
    assert post('/api/key', {'key': 427, 'observed_sequence': 1})[0] == 409
    assert len(state.pending) == 1
    checks.append('one authenticated key pending; duplicate blocked')
    state.pending.clear()
    state.update(phase='finished', ready=False, busy=False, message='fixture failed',
                 result={'health_pass': False, 'API16_restored': False})
    assert post('/api/stop', {}) == (200, {'finished': True})
    assert post('/api/final-ack', {'receipt_id': 'wrong'})[0] == 409
    assert post('/api/final-ack', {'receipt_id': state.final_receipt_id}, token=False)[0] == 403
    checks.append('late stop cannot rewrite final result; wrong or unauthenticated ACK rejected')
    delivery = []
    waiter = threading.Thread(target=lambda: delivery.append(web.wait_for_final_receipt(state)))
    waiter.start()
    time.sleep(2.1)
    assert waiter.is_alive() and json.loads(get('/api/status')[2])['phase'] == 'finished'
    assert post('/api/final-ack', {'receipt_id': state.final_receipt_id}) == (200, {'acknowledged': True})
    waiter.join(timeout=2)
    assert not waiter.is_alive() and delivery[0]['acknowledged']
    checks.append('terminal result remains reachable beyond old 2s window; matching ACK closes bounded wait')
finally:
    state.final_receipt_close.set()
    server.shutdown(); server.server_close(); thread.join(timeout=3)
assert not thread.is_alive()
print(json.dumps({'status': 'PASS_V21_LOOPBACK_HTTP', 'checks': checks,
                  'web_sha256': hashlib.sha256((HERE/'trial_web_v21_final_timing.py').read_bytes()).hexdigest(),
                  'guest_started': False, 'server_thread_reaped': True}, ensure_ascii=False, indent=2))
