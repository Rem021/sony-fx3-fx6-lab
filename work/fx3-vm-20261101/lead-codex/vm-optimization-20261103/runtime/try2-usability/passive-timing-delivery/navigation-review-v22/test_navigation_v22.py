#!/usr/bin/env python3
"""Host-only state and real HTTP checks using immutable historical FX3 PNGs."""
import hashlib
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import trial_web_v22_navigation_review as web

HERE = Path(__file__).resolve().parent
RUN = HERE.parents[1] / 'runs/try2passivetiming-internal-v21-2383af57'
NAMES = ('internal-observe-01', 'trial-step-01-key-1ab',
         'internal-observe-02', 'trial-step-02-key-015', 'internal-observe-03')
frames = []
for name in NAMES:
    meta = json.loads((RUN / (name + '.json')).read_text())
    data = (RUN / (name + '.png')).read_bytes()
    assert hashlib.sha256(data).hexdigest() == meta['PNG_sha256']
    frames.append((data, meta))

state = web.TrialState('HOST_ONLY', 60, 4096)
server, thread = web.start_server(state, 0)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
checks = []

def post(path, body):
    request = urllib.request.Request(state.url + path, json.dumps(body).encode(), {
        'Content-Type':'application/json', 'X-Trial-Token':state.token, 'Origin':state.url})
    try:
        response = opener.open(request, timeout=3)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, json.loads(response.read())

def ident(frame):
    return {'step':state.review_step, 'observed_sequence':frame['sequence'],
            'PNG_sha256':frame['PNG_sha256'], 'content_generation':frame['content_generation'],
            'request_id':format(frame['sequence'], '032x')}

try:
    state.publish(*frames[0]); state.update(phase='ready', ready=True)
    standby = dict(state.frame)
    assert post('/api/key', {'key':427,'observed_sequence':standby['sequence']})[0] == 202
    assert state.take()['key'] == 427
    state.update(steps=1)
    state.publish(*frames[1]); state.require_visual_review(1,'visual_changed',True)
    flash = dict(state.frame)
    assert state.snapshot()['ready'] is False
    assert post('/api/key', {'key':21,'observed_sequence':flash['sequence']})[0] == 409
    assert not state.pending
    checks.append('NO CARD blink does not release key gate or enqueue input')
    state.publish(*frames[2]); full = dict(state.frame)
    assert post('/api/confirm-visual', ident(flash))[0] == 409
    assert state.review_required and not state.pending
    checks.append('stale blink identity rejected after full menu transition')
    full_confirmation = ident(full)
    code, ack = post('/api/confirm-visual', full_confirmation)
    assert code == 200 and ack == {'confirmed':True,'guest_input_written':False, **full_confirmation}
    assert state.snapshot()['review_confirmation'] == {**full_confirmation, 'guest_input_written':False}
    assert not state.pending and state.snapshot()['ready']
    checks.append('full historical menu identity can clear host gate only')
    assert post('/api/key', {'key':21,'observed_sequence':flash['sequence']})[0] == 409
    assert post('/api/key', {'key':21,'observed_sequence':full['sequence']})[0] == 202
    assert state.take()['key'] == 21
    checks.append('old image cannot send next key; current full image can')
    state.update(steps=2)
    state.publish(*frames[3]); partial = dict(state.frame)
    state.require_visual_review(2,'visual_changed',True)
    assert post('/api/key', {'key':48,'observed_sequence':partial['sequence']})[0] == 409
    state.publish(*frames[4]); category = dict(state.frame)
    assert post('/api/confirm-visual', ident(partial))[0] == 409
    assert post('/api/confirm-visual', ident(category))[0] == 200
    checks.append('partial category transition remains locked until current image review')
    state.require_visual_review(2,'no_change_observed',False)
    # Repeated commits with identical bytes retain content generation and allow
    # manual acknowledgement of a legitimate static/no-change command.
    same = dict(category, sequence=category['sequence']+100)
    state.publish(frames[4][0], same)
    assert state.frame['content_generation'] == category['content_generation']
    assert post('/api/confirm-visual', ident(category))[0] == 200
    assert state.snapshot()['ready']
    checks.append('static no-change may be reviewed without invented pixel change')
    state.require_visual_review(2,'visual_changed',True)
    assert post('/api/stop', {})[0] == 202
    assert post('/api/confirm-visual', ident(state.frame))[0] == 409
    assert not state.pending
    checks.append('End remains possible with review pending and blocks late confirmation')
    state.update(phase='finished', ready=False, result={'fixture_only':True})
    assert post('/api/final-ack', {'receipt_id':state.final_receipt_id})[0] == 200
    checks.append('final receipt and ACK remain functional')
finally:
    state.final_receipt_close.set()
    server.shutdown(); server.server_close(); thread.join(timeout=3)
assert not thread.is_alive()
cycle = web.TrialState('A_B_A_STALE', 60, 4096)
for seq, i in ((100,0),(101,1),(102,0)):
    cycle.publish(frames[i][0], dict(frames[i][1], sequence=seq))
cycle.update(phase='ready', ready=True)
assert cycle.submit({'key':427,'observed_sequence':100})[0] == 409
assert cycle.submit({'key':427,'observed_sequence':102})[0] == 202
checks.append('A→B→A stale visual generation cannot submit a new guest key')
print(json.dumps({'status':'PASS', 'checks':checks, 'guest_started':False,
                  'historical_PNG_SHA256':[meta['PNG_sha256'] for _,meta in frames],
                  'server_thread_reaped':True}, ensure_ascii=False, indent=2))
