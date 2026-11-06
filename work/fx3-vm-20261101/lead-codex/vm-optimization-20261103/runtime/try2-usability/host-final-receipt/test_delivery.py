"""Actual loopback final-receipt protocol; fixture states, never QEMU."""
import hashlib
import importlib.util
import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
checks = []

def module(name):
    path = PARENT/(name+'.py')
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def post(state, path, body, token=True):
    headers = {'Content-Type':'application/json', 'Origin':state.url}
    if token:
        headers['X-Trial-Token'] = state.token
    req = urllib.request.Request(state.url+path, json.dumps(body).encode(), headers)
    try:
        response = opener.open(req, timeout=3)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, json.loads(response.read())

def get(state):
    with opener.open(state.url+'/api/status',timeout=3) as response:
        return json.loads(response.read())

def close(server, thread):
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)
    assert not thread.is_alive()

old = module('trial_web_v4_resilient')
legacy = old.TrialState('HOST_FIXTURE_OLD_NO_GUEST',60,4096)
legacy.update(phase='finished',message='fixture final',result={'health_pass':False})
server, thread = old.start_server(legacy,0)
try:
    assert post(legacy,'/api/stop',{})[0] == 202
    assert get(legacy)['phase'] == 'stopping'
    checks.append('baseline reproduced: late stop regresses finished to stopping')
finally:
    close(server,thread)

web = module('trial_web_v5_final_receipt')
state = web.TrialState('HOST_FIXTURE_NEW_NO_GUEST',60,4096)
server, thread = web.start_server(state,0)
waiter = None
try:
    assert get(state)['final_receipt_id'] is None
    assert post(state,'/api/final-ack',{'receipt_id':state.final_receipt_id})[0] == 409
    assert not state.final_receipt_seen.is_set()
    checks.append('unfinished session cannot expose or accept final receipt')
    final_result = {'health_pass':False,'qemu_exit':None,'API16_restored':False}
    state.update(phase='finished',message='收尾检查未全部通过',result=final_result)
    snapshot = get(state)
    assert snapshot['final_receipt_id'] == state.final_receipt_id
    result = []
    waiter = threading.Thread(target=lambda:result.append(web.wait_for_final_receipt(state)))
    waiter.start()
    time.sleep(2.2)  # The old runner closed its server after only two seconds.
    assert waiter.is_alive()
    assert get(state)['phase'] == 'finished'
    checks.append('final status remains reachable after old two-second close window')
    assert post(state,'/api/final-ack',{'receipt_id':state.final_receipt_id},token=False)[0] == 403
    assert post(state,'/api/final-ack',{'receipt_id':'wrong-receipt'})[0] == 409
    assert waiter.is_alive() and not state.final_receipt_seen.is_set()
    checks.append('unauthenticated or mismatched receipt cannot close delivery wait')
    assert post(state,'/api/stop',{}) == (200,{'finished':True})
    assert get(state)['phase'] == 'finished' and get(state)['result'] == final_result
    checks.append('late or repeated stop leaves terminal result unchanged')
    before = time.monotonic()
    assert post(state,'/api/final-ack',{'receipt_id':state.final_receipt_id}) == (200,{'acknowledged':True})
    waiter.join(timeout=2)
    assert not waiter.is_alive() and time.monotonic()-before < 2
    assert result[0]['acknowledged'] and result[0]['end_reason'] == 'browser_ack'
    assert post(state,'/api/final-ack',{'receipt_id':state.final_receipt_id})[0] == 200
    assert get(state)['result'] == final_result
    checks.append('matching acknowledgement ends wait promptly without converting failure to success')
finally:
    state.final_receipt_close.set()
    if waiter:
        waiter.join(timeout=2)
    close(server,thread)

unseen = web.TrialState('HOST_FIXTURE_CLOSED_TAB',60,4096)
unseen.update(phase='finished')
result = web.wait_for_final_receipt(unseen,timeout=0.05)
assert result['acknowledged'] is False and result['end_reason'] == 'timeout'
checks.append('closed browser expires bounded grace without false acknowledgement')
unseen.final_receipt_close.set()
result = web.wait_for_final_receipt(unseen)
assert not result['acknowledged'] and result['end_reason'] == 'local_exit'
assert unseen.phase == 'finished'
checks.append('local exit shortens wait while preserving terminal phase and unacknowledged truth')
for invalid in (-1,31):
    try:
        web.wait_for_final_receipt(unseen,invalid)
    except ValueError:
        pass
    else:
        raise AssertionError('unbounded grace accepted')
checks.append('grace outside zero-to-thirty seconds rejected')
print(json.dumps({'status':'PASS_FINAL_RECEIPT_HTTP_FIXTURE','checks':checks,
                  'web_candidate_sha256':hashlib.sha256((PARENT/'trial_web_v5_final_receipt.py').read_bytes()).hexdigest(),
                  'server_threads_reaped':True,'scope':'Actual loopback HTTP and bounded host thread; no browser rendering or guest execution'},ensure_ascii=False,indent=2))
