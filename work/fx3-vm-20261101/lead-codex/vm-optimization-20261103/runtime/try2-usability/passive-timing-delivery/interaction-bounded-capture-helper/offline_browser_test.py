#!/usr/bin/env python3
"""Pinned r17 PAGE/TrialState and dedicated Chrome fixture; no VM or key mutation."""
import hashlib
import importlib.util
import json
import subprocess
import time
import uuid
from pathlib import Path

from bounded_capture_cli import capture, browser as real_browser, MENU_SHA

HERE = Path(__file__).resolve().parent
DEL = HERE.parent
RUN = DEL.parent / 'runs/v25gate-n64-r17-c33f8c46'
PAGE = DEL / 'v25-r17-tail-receipt/trial_web_v22_navigation_review.py'
DEADLINE = DEL / 'interaction-deadline-helper/deadline.js'
INTERMEDIATE = RUN / 'trial-step-01-key-1ab.png'
COMPLETE = RUN / 'trial-final.png'
PINS = {str(PAGE): 'cfd4239effb34c8be3381eff9c1de3ebf0f6ca4d10af16c86c167e3d76ee82bb',
        str(DEADLINE): '93af6b5ce6eb3f736eeed38320c990c6a05701cb6c883493589dadaf4bb57916',
        str(COMPLETE): MENU_SHA}
sha = lambda data: hashlib.sha256(data).hexdigest()
for path, expected in PINS.items():
    assert sha(Path(path).read_bytes()) == expected, path
assert sha(INTERMEDIATE.read_bytes()) != MENU_SHA
spec = importlib.util.spec_from_file_location('r17_capture_page', PAGE)
page = importlib.util.module_from_spec(spec)
spec.loader.exec_module(page)
SESSION = 'fx3-deadline-bounded-' + uuid.uuid4().hex[:8]
EVIDENCE = HERE / 'evidence' / ('run-' + uuid.uuid4().hex[:8])
EVIDENCE.mkdir(parents=True)
RESULT = {'scope':'offline real r17 PAGE/TrialState + dedicated Chrome; no QEMU',
          'session':SESSION, 'pinned_inputs':PINS, 'cases':{}, 'evidence_dir':str(EVIDENCE)}


def browser(*args, source=None):
    return real_browser(SESSION, list(args), source=source)


def js(code):
    return json.loads(browser('eval', '--stdin', source=code))


def wait(predicate, timeout=4):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        value = predicate()
        if value:
            return value
        time.sleep(.05)
    raise AssertionError('fixture DOM wait expired')


class Fixture:
    def __init__(self, label):
        self.label = label
        self.launch = str(uuid.uuid4())
        self.state = page.TrialState('offline-bounded-' + label, 3600, 4096)
        self.state.update(phase='ready', ready=True, launch_status='running',
                          launch_request_id=self.launch, message='offline capture fixture', steps=1)
        self.publish(INTERMEDIATE.read_bytes(), 32)
        self.state.require_visual_review(1, 'visual_pending', True)
        self.key_count = 0
        orig_submit = self.state.submit
        def count_submit(*args, **kwargs):
            self.key_count += 1
            return orig_submit(*args, **kwargs)
        self.state.submit = count_submit
        self.server, self.thread = page.start_server(self.state, 0)
        self.url = self.state.url + '/'
        browser('open', self.url)
        browser('set', 'viewport', '1280', '1200')
        wait(lambda: js('({ok:!!lastStatus?.review_required&&shownSHA===lastStatus.frame?.PNG_sha256&&!confirmButton.disabled})')['ok'])
        deadline_source = DEADLINE.read_text()
        h = js(deadline_source + '(' + json.dumps({'expectedURL':self.url,
                                                   'expectedLaunchId':self.launch}) + ')')
        assert h['deadline_ms'] == 20000
        self.nonce = str(uuid.uuid4())
        arm = js('window.__fx3InteractionDeadlineV1.arm(' + json.dumps(self.nonce) + ')')
        assert arm['current']['state'] == 'armed'
        self.due = arm['current']['due_ms']

    def publish(self, data, sequence):
        self.state.publish(data, {'sequence':sequence, 'PNG_sha256':sha(data),
                                  'all_zero_pixels':False, 'width':960, 'height':640})

    def capture(self, suffix, *, nonce=None, browser_call=None):
        out = EVIDENCE / (self.label + '-' + suffix)
        r = capture(SESSION, self.url, self.launch, nonce or self.nonce, out,
                    browser_call=browser_call or real_browser)
        dom = js('({phase:lastStatus.phase,shownSHA,displayedGeneration,displayed,frame:lastStatus.frame,alarm:window.__fx3InteractionDeadlineV1.status(),reviewAwaiting,pendingConfirm})')
        RESULT['cases'][self.label + '-' + suffix] = {'capture':r, 'dom':dom,
            'key_count':self.key_count,
            'confirm_count':len([e for e in self.state.events if 'confirm' in str(e).lower()])}
        return r

    def close(self):
        try: browser('close')
        except Exception: pass
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)
        assert not self.thread.is_alive()


def case_transition():
    f = Fixture('transition')
    try:
        # Fixture publication is external to the helper and never a guest input.
        import threading
        t = threading.Timer(.35, lambda: f.publish(COMPLETE.read_bytes(), 33))
        t.start()
        r = f.capture('target')
        t.join()
        assert r['status'] == 'qualified_screenshot_for_operator_review', r
        assert r['before_eval']['before']['png_sha256'] == MENU_SHA
        assert r['after_eval']['png_sha256'] == MENU_SHA
        assert f.key_count == 0 and r['confirm_calls'] == 0 and r['alarm_mutations'] == 0
        assert js('window.__fx3InteractionDeadlineV1.status().current.state') == 'armed'
        # Frozen image file is shown to the agent separately; helper does not judge MENU semantics.
    finally: f.close()


def case_no_match():
    f = Fixture('no-match')
    try:
        r = f.capture('bounded')
        assert r['status'] == 'no_qualified_screenshot' and not r['screenshot_attempted'], r
        assert r['before_eval']['waited_ms'] <= 8400, r
        assert f.key_count == 0 and js('window.__fx3InteractionDeadlineV1.status().current.state') == 'armed'
    finally: f.close()


def case_wrong_nonce():
    f = Fixture('wrong-nonce')
    try:
        r = f.capture('refused', nonce=str(uuid.uuid4()))
        assert r['status'] == 'no_qualified_screenshot' and not r['screenshot_attempted'], r
        assert f.key_count == 0
    finally: f.close()


def case_expired():
    f = Fixture('expired')
    try:
        # Exercise the actual production 20s alarm once; no clock or source rewrite.
        wait(lambda: js('window.__fx3InteractionDeadlineV1.status().current.state') == 'expired', 22)
        r = f.capture('refused-after-expiry')
        assert r['status'] == 'no_qualified_screenshot' and not r['screenshot_attempted'], r
        assert f.key_count == 0
    finally: f.close()


def case_screenshot_changed():
    f = Fixture('changed')
    try:
        f.publish(COMPLETE.read_bytes(), 33)
        wait(lambda: js('shownSHA') == MENU_SHA)
        def changed_browser(session, args, *, source=None, timeout=15):
            raw = real_browser(session, args, source=source, timeout=timeout)
            if args[0] == 'screenshot':
                f.publish(INTERMEDIATE.read_bytes(), 34)
                wait(lambda: js('shownSHA') == sha(INTERMEDIATE.read_bytes()))
            return raw
        r = f.capture('post-rejected', browser_call=changed_browser)
        assert r['status'] == 'no_qualified_screenshot' and r['screenshot_attempted'], r
        assert r['reason'] == 'post_screenshot_identity_or_reserve_changed'
        assert f.key_count == 0
    finally: f.close()


if __name__ == '__main__':
    try:
        case_transition()
        case_no_match()
        case_wrong_nonce()
        case_expired()
        case_screenshot_changed()
        RESULT['passed'] = True
    except BaseException as e:
        RESULT['passed'] = False
        RESULT['error'] = repr(e)
        raise
    finally:
        (EVIDENCE / 'RESULT.json').write_text(json.dumps(RESULT, ensure_ascii=False, indent=2) + '\n')
        p = subprocess.run(['agent-browser','--session',SESSION,'session','info','--json'],
                           capture_output=True,text=True)
        (EVIDENCE / 'BROWSER-CLEANUP.json').write_text(p.stdout if p.returncode == 0 else p.stderr)
