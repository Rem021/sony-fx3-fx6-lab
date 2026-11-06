#!/usr/bin/env python3
"""Real r12 PAGE/TrialState, real Chrome, no VM or guest resources."""
import hashlib
import importlib.util
import json
import struct
import subprocess
import time
import traceback
import uuid
import zlib
from collections import Counter
from pathlib import Path

from deadline_cli import operate

HERE = Path(__file__).resolve().parent
MODULE = HERE.parent / 'v25-r12-confirmation-progress/trial_web_v22_navigation_review.py'
PIN = 'cfd4239effb34c8be3381eff9c1de3ebf0f6ca4d10af16c86c167e3d76ee82bb'
SESSION = 'fx3-deadline-offline'
EVIDENCE = HERE / 'evidence-final'
SHORT_MS = 1200
SOURCE = (HERE / 'deadline.js').read_text()
assert SOURCE.count('const DEADLINE_MS = 20_000;') == 1
SHORT = SOURCE.replace('const DEADLINE_MS = 20_000;', f'const DEADLINE_MS = {SHORT_MS};')
assert hashlib.sha256(MODULE.read_bytes()).hexdigest() == PIN
spec = importlib.util.spec_from_file_location('original_r12_page', MODULE)
page = importlib.util.module_from_spec(spec)
spec.loader.exec_module(page)
RESULT = {'module': str(MODULE), 'module_SHA256_before': PIN, 'short_deadline_ms': SHORT_MS,
          'source_SHA256': hashlib.sha256(SOURCE.encode()).hexdigest(),
          'cases': {}, 'cleanup': {}}


def browser(*args, code=None):
    p = subprocess.run(['agent-browser', '--session', SESSION, *args], input=code,
                       capture_output=True, text=True, timeout=15)
    if p.returncode:
        raise AssertionError(f'{args}: {p.stdout} {p.stderr}')
    return p.stdout


def js(code):
    return json.loads(browser('eval', '--stdin', code=code))


def call(action, nonce=None):
    return js(f'window.__fx3InteractionDeadlineV1[{json.dumps(action)}]({json.dumps(nonce)})')


def await_check(predicate, timeout=4):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        value = predicate()
        if value:
            return value
        time.sleep(.04)
    raise AssertionError('bounded wait timed out')


def image():
    def chunk(k, d):
        return struct.pack('!I', len(d)) + k + d + struct.pack('!I', zlib.crc32(k + d) & 0xffffffff)
    row = b'\0' + bytes([200, 80, 20]) * 12
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 12, 12, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(row * 12)) + chunk(b'IEND', b'')


class Fixture:
    def __init__(self, name):
        self.state = page.TrialState('offline-deadline-' + name, 3600, 32)
        self.launch = str(uuid.uuid4())
        self.state.update(phase='ready', ready=True, launch_status='running',
                          launch_request_id=self.launch, message='Offline deadline fixture')
        data = image()
        self.state.publish(data, {'sequence': 1, 'PNG_sha256': hashlib.sha256(data).hexdigest(),
                                 'all_zero_pixels': False, 'width': 12, 'height': 12})
        self.counts = Counter()
        self.stop_times = []
        for method, label in [('submit', 'key'), ('confirm_visual', 'confirm'),
                              ('request_stop', 'stop'), ('request_launch', 'start'),
                              ('acknowledge_final', 'final_ack')]:
            original = getattr(self.state, method)
            def wrapped(*args, original=original, label=label):
                self.counts[label] += 1
                if label == 'stop':
                    self.stop_times.append(time.monotonic())
                return original(*args)
            setattr(self.state, method, wrapped)
        self.server, self.thread = page.start_server(self.state, 0)
        self.url = self.state.url + '/'

    def open(self):
        browser('open', self.url)
        browser('set', 'viewport', '1280', '1200')
        await_check(lambda: js('typeof lastStatus!=="undefined"&&lastStatus&&lastStatus.phase==="ready"&&!!shownSHA'))

    def install(self, config=None, source=SHORT):
        c = config or {'expectedURL': self.url, 'expectedLaunchId': self.launch}
        return js(source + '(' + json.dumps(c) + ')')

    def stats(self):
        return {'requests': {k: self.counts[k] for k in ['key', 'confirm', 'stop', 'start', 'final_ack']},
                'steps': self.state.steps, 'pending': len(self.state.pending),
                'busy': self.state.busy, 'phase': self.state.phase, 'stop_event': self.state.stop.is_set()}

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        assert not self.thread.is_alive()


def nonce():
    return str(uuid.uuid4())


def expired(f):
    return await_check(lambda: f.counts['stop'] == 1)


def save(name, f, extra=None):
    helper = js('window.__fx3InteractionDeadlineV1?window.__fx3InteractionDeadlineV1.status():null')
    shot = EVIDENCE / (name + '.png')
    browser('screenshot', '--full', str(shot))
    dom = js('({endDisabled:document.querySelector("#end").disabled,phase:lastStatus.phase,ending,finished,menuDisabled:document.querySelector("[data-key="+JSON.stringify("427")+"]").disabled})')
    RESULT['cases'][name] = {'helper': helper, 'stats': f.stats(), 'browser': dom,
                             'extra': extra, 'screenshot': shot.name,
                             'screenshot_SHA256': hashlib.sha256(shot.read_bytes()).hexdigest(), 'passed': True}


def run_case(name, action):
    f = Fixture(name)
    try:
        f.open()
        action(f)
    finally:
        f.close()


def basic(f):
    f.install(); before = time.monotonic(); a = nonce(); call('arm', a)
    expired(f); time.sleep(.15)
    h = call('status'); events = [e for e in h['events'] if e['event'] == 'end_click']
    assert len(events) == 1 and events[0]['elapsed_ms'] >= SHORT_MS
    assert f.counts['stop'] == 1 and f.counts['key'] == f.counts['confirm'] == 0
    assert f.state.phase == 'stopping'
    save('uncancelled_once', f, {'server_elapsed_since_before_arm_eval_ms': (f.stop_times[0]-before)*1000})


def timely(f):
    f.install(); a = nonce(); armed = call('arm', a); time.sleep(.1); cancelled = call('cancel', a)
    assert cancelled['current']['state'] == 'cancelled' and cancelled['current']['nonce'] == a
    time.sleep(SHORT_MS/1000+.1)
    assert f.counts['stop'] == f.counts['key'] == f.counts['confirm'] == 0
    disposed = call('dispose'); assert disposed['sealed']
    save('timely_cancel', f, {'armed': armed, 'cancel_receipt': cancelled})


def stale(f):
    f.install(); a, b = nonce(), nonce(); call('arm', a); call('cancel', a)
    armed = call('arm', b); ignored = call('cancel', a)
    assert ignored['current']['nonce'] == b and ignored['current']['state'] == 'armed'
    assert ignored['current']['due_ms'] == armed['current']['due_ms']
    expired(f); assert f.counts['key'] == f.counts['confirm'] == 0
    save('old_nonce_does_not_cancel_new', f, {'old': a, 'new': b})


def duplicate(f):
    f.install(); a = nonce(); original = call('arm', a); time.sleep(.65)
    same = call('arm', a); different = call('arm', nonce())
    assert same['current']['due_ms'] == different['current']['due_ms'] == original['current']['due_ms']
    assert different['current']['nonce'] == a
    # Reinstalling the helper cannot replace its existing timeout either.
    assert f.install()['current']['due_ms'] == original['current']['due_ms']
    expired(f); assert f.counts['stop'] == 1
    save('repeat_arm_no_extension', f)


def wrong_url(f):
    try: f.install({'expectedURL': f.url + '?wrong=1', 'expectedLaunchId': f.launch})
    except AssertionError as e: error = str(e)
    else: raise AssertionError('wrong URL accepted')
    assert js('!window.__fx3InteractionDeadlineV1')
    assert not f.counts
    save('wrong_URL_refused', f, {'error': error})


def wrong_dom(f):
    js('document.querySelector("#end").textContent="wrong DOM";true')
    try: f.install()
    except AssertionError as e: error = str(e)
    else: raise AssertionError('wrong DOM accepted')
    assert js('!window.__fx3InteractionDeadlineV1')
    assert not f.counts
    save('wrong_DOM_refused', f, {'error': error})


def pending(f):
    f.install(); call('arm', nonce())
    browser('click', 'button[data-key="427"]') # Explicit fixture setup; alarm never sends keys.
    await_check(lambda: f.counts['key'] == 1 and len(f.state.pending) == 1)
    await_check(lambda: js('lastStatus.busy&&document.querySelector("[data-key=\\"427\\"]").disabled'))
    observed = js('({busy:lastStatus.busy,keyDisabled:document.querySelector("[data-key=\\"427\\"]").disabled,endDisabled:document.querySelector("#end").disabled})')
    assert observed['busy'] and observed['keyDisabled'] and not observed['endDisabled']
    expired(f)
    assert f.counts['stop'] == f.counts['key'] == 1 and f.counts['confirm'] == 0
    save('real_key_pending_End_enabled', f, {'pending_observation': observed,
                                           'fixture_explicit_key_clicks': 1, 'alarm_added_key_requests': 0})


def already_end(f):
    f.install(); call('arm', nonce()); browser('click', '#end')
    await_check(lambda: f.counts['stop'] == 1)
    time.sleep(SHORT_MS/1000+.15)
    h = call('status'); assert any(e['event']=='already_stopping_or_disabled' for e in h['events'])
    assert f.counts['stop'] == 1 and not any(e['event']=='end_click' for e in h['events'])
    save('existing_End_not_clicked_twice', f)


def terminal(f):
    f.install(); call('arm', nonce())
    f.state.update(phase='finished', ready=False, message='offline terminal fixture')
    await_check(lambda: js('finished'))
    time.sleep(SHORT_MS/1000+.15)
    a = call('arm', nonce())
    assert a['current']['state']=='expired' and f.state.phase=='finished' and f.counts['stop']==0
    assert f.counts['key'] == f.counts['confirm'] == 0
    save('terminal_not_reversed', f)


def blocked(f):
    f.install(); a=nonce(); call('arm', a)
    h = js('(() => { const until=performance.now()+1800; while(performance.now()<until){}; return window.__fx3InteractionDeadlineV1.cancel('+json.dumps(a)+'); })()')
    expired(f); assert h['current']['state']=='expired' and h['current']['elapsed_ms']>=1800
    assert f.counts['stop']==1 and f.counts['key']==f.counts['confirm']==0
    save('blocked_event_loop_is_not_hard_deadline', f)


def production_wrapper(f):
    installed=operate(SESSION,f.url,f.launch,'install'); assert installed['deadline_ms']==20000
    a=nonce(); armed=operate(SESSION,f.url,f.launch,'arm',a)
    cancelled=operate(SESSION,f.url,f.launch,'cancel',a)
    assert armed['current']['nonce']==cancelled['current']['nonce']==a and cancelled['current']['state']=='cancelled'
    operate(SESSION,f.url,f.launch,'dispose')
    assert not f.counts
    save('production_20s_wrapper_arm_cancel', f, {'arm_receipt':armed,'cancel_receipt':cancelled})


if __name__ == '__main__':
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE/'deadline-short.js').write_text(SHORT)
    try:
        for name, action in [('basic',basic),('timely',timely),('stale',stale),
                             ('duplicate',duplicate),('wrong_url',wrong_url),('wrong_dom',wrong_dom),
                             ('pending',pending),('already_end',already_end),('terminal',terminal),
                             ('blocked',blocked),('production_wrapper',production_wrapper)]:
            run_case(name,action)
        RESULT['passed'] = True
    except Exception:
        RESULT['passed'] = False
        RESULT['error'] = traceback.format_exc()
        raise
    finally:
        RESULT['module_SHA256_after'] = hashlib.sha256(MODULE.read_bytes()).hexdigest()
        RESULT['source_SHA256_after'] = hashlib.sha256((HERE/'deadline.js').read_bytes()).hexdigest()
        RESULT['cleanup']['browser_close'] = browser('close').strip()
        RESULT['cleanup']['harness_threads_joined'] = True
        (EVIDENCE/'RESULT.json').write_text(json.dumps(RESULT,ensure_ascii=False,indent=2)+'\n')
