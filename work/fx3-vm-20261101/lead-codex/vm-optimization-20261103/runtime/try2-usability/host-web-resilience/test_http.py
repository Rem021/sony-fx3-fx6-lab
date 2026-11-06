"""Loopback HTTP contract test with a fake guest state; never starts QEMU."""
from pathlib import Path
import base64
import hashlib
import importlib.util
import json
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
MODULE = HERE.parent / 'trial_web_v4_resilient.py'
spec = importlib.util.spec_from_file_location('host_test_trial_web', MODULE)
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)
state = web.TrialState('HOST_TEST_NO_GUEST', 60, 4096)
png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWZkAAAAASUVORK5CYII=')
sha = hashlib.sha256(png).hexdigest()
state.publish(png, {'sequence': 1, 'PNG_sha256': sha, 'pixel_source_sequence': 1})
state.update(ready=True, phase='ready')
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
    code, headers, body = get('/')
    assert code == 200 and b'AbortController' in body and b'__TOKEN__' not in body
    assert "frame-ancestors 'none'" in headers['Content-Security-Policy']
    checks.append('actual server serves bounded-request candidate and existing CSP')
    code, headers, body = get('/frame.png')
    assert body == png and headers['X-Frame-PNG-SHA256'] == sha
    checks.append('frame bytes and identity headers agree')
    assert post('/api/key', {'key': 427, 'observed_sequence': 1}, token=False)[0] == 403
    assert len(state.pending) == 0
    checks.append('unauthenticated request never enters input queue')
    code, ack = post('/api/key', {'key': 427, 'observed_sequence': 1})
    assert code == 202 and ack['next_step'] == 1 and len(state.pending) == 1
    assert post('/api/key', {'key': 427, 'observed_sequence': 1})[0] == 409
    assert len(state.pending) == 1
    checks.append('one accepted key, concurrent duplicate blocked, no guest write')
    assert post('/api/stop', {})[0] == 202
    status = json.loads(get('/api/status')[2])
    assert status['phase'] == 'stopping' and status['ready'] is False and state.stop.is_set()
    assert status['result'] is None
    checks.append('stop acknowledgement is distinct from final completion status')
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)
assert not thread.is_alive()
print(json.dumps({'status': 'PASS_LOOPBACK_HTTP_FAKE_GUEST', 'checks': checks,
                  'module_sha256': hashlib.sha256(MODULE.read_bytes()).hexdigest(),
                  'server_thread_reaped': True,
                  'scope': 'Real loopback HTTP with fixture state; no browser rendering, QEMU, firmware input or VM cleanup proof'}, indent=2))
