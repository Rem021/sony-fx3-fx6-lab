"""Real Chrome with r18 PAGE/TrialState and pinned operator helpers; no VM."""
import hashlib
import importlib.util
import json
import subprocess
import sys
import threading
import time
import uuid
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEL = ROOT.parent
OPS = ROOT / 'operator-helpers'
OLD = {'deadline': (DEL / 'interaction-deadline-helper/deadline.js').read_text(),
       'capture': (DEL / 'interaction-bounded-capture-helper-r3/bounded_capture.js').read_text(),
       'confirm': (DEL / 'interaction-explicit-confirm-helper/explicit_confirm.js').read_text()}
sys.path.insert(0, str(OPS))
from bounded_capture_cli import capture, MENU_SHA  # noqa: E402
from explicit_confirm_cli import operate  # noqa: E402

spec = importlib.util.spec_from_file_location('r18_trial_page', ROOT / 'trial_web_v22_navigation_review.py')
page = importlib.util.module_from_spec(spec)
spec.loader.exec_module(page)
run_png = DEL.parent / 'runs/v25gate-n64-r17-c33f8c46'
INTERMEDIATE = (run_png / 'trial-step-01-key-1ab.png').read_bytes()
COMPLETE = (run_png / 'trial-final.png').read_bytes()
assert hashlib.sha256(COMPLETE).hexdigest() == MENU_SHA
SESSION = 'fx3-deadline-r18-' + uuid.uuid4().hex[:8]
OUT = ROOT / 'evidence' / ('helper-run-' + uuid.uuid4().hex[:8])
OUT.mkdir(parents=True)
RESULT = {'scope': 'offline Chrome with actual r18 PAGE and helper JS; no VM',
          'cases': {}, 'session': SESSION, 'evidence_dir': str(OUT)}


def browser(*args, source=None, expect_error=False):
    p = subprocess.run(['agent-browser', '--session', SESSION, *args], input=source,
                       text=True, capture_output=True, timeout=20)
    if expect_error:
        assert p.returncode != 0, (args, p.stdout)
        return p.stdout + p.stderr
    if p.returncode:
        raise AssertionError(f'browser {args}: {p.stdout} {p.stderr}')
    return p.stdout


def js(source):
    return json.loads(browser('eval', '--stdin', source=source))


def wait(predicate, why, timeout=5):
    until = time.monotonic() + timeout
    last = None
    while time.monotonic() < until:
        last = predicate()
        if last:
            return last
        time.sleep(.04)
    raise AssertionError(f'{why}: {last}')


class Fixture:
    def __init__(self, name):
        self.name = name
        self.launch = str(uuid.uuid4())
        self.nonce = str(uuid.uuid4())
        self.counts = Counter()
        self.state = page.TrialState('offline-r18-' + name, 3600, 4096)
        self.state.update(phase='ready', ready=True, launch_status='running',
                          launch_request_id=self.launch, steps=1, message='offline helper fixture')
        self.publish(INTERMEDIATE, 32)
        self.state.require_visual_review(1, 'visual_changed', True)
        for method, label in [('submit', 'key'), ('confirm_visual', 'confirm'),
                              ('request_stop', 'stop')]:
            orig = getattr(self.state, method)
            def counted(*args, orig=orig, label=label):
                self.counts[label] += 1
                return orig(*args)
            setattr(self.state, method, counted)
        self.server, self.thread = page.start_server(self.state, 0)
        self.url = self.state.url + '/'
        browser('open', self.url)
        browser('set', 'viewport', '1280', '1200')
        wait(lambda: js('({ready:!!lastStatus&&lastStatus.review_required&&shownSHA===lastStatus.frame?.PNG_sha256&&!confirmButton.disabled})')['ready'],
             'PAGE review ready')

    def publish(self, data, seq):
        self.state.publish(data, {'sequence': seq, 'PNG_sha256': hashlib.sha256(data).hexdigest(),
                                  'all_zero_pixels': False, 'width': 960, 'height': 640})

    def install(self, source=None):
        script = source or (OPS / 'deadline.js').read_text()
        return js(script + '(' + json.dumps({'expectedURL': self.url,
                                              'expectedLaunchId': self.launch}) + ')')

    def arm(self):
        value = js('window.__fx3InteractionDeadlineV1.arm(' + json.dumps(self.nonce) + ')')
        assert value['current']['state'] == 'armed' and value['deadline_ms'] == 20000
        return value

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        assert not self.thread.is_alive()


def record(name, value):
    RESULT['cases'][name] = value


def run():
    f = Fixture('success')
    try:
        old_error = browser('eval', '--stdin', source=OLD['deadline'] + '(' + json.dumps({
            'expectedURL': f.url, 'expectedLaunchId': f.launch}) + ')', expect_error=True)
        assert 'PAGE fingerprint' in old_error
        assert js('!window.__fx3InteractionDeadlineV1') is True
        record('old_deadline_rejected_new_PAGE', {'error': old_error[-300:], 'counts': dict(f.counts)})
        installed = f.install()
        armed = f.arm()
        assert installed['version'] == 1 and armed['current']['nonce'] == f.nonce
        record('new_deadline_installed_armed', {'due_ms': armed['current']['due_ms'],
                                                'deadline_ms': armed['deadline_ms']})

        old_capture = js(OLD['capture'] + '(' + json.dumps({
            'url': f.url, 'launch_id': f.launch, 'nonce': f.nonce,
            'step': 1, 'reference_sha': MENU_SHA}) + ')')
        assert old_capture['status'] == 'no_qualified_screenshot'
        assert 'PAGE_fingerprint' in old_capture['reason']
        record('old_capture_rejected_new_PAGE', {'status': old_capture['status'],
                                                  'reason': old_capture['reason']})

        timer = threading.Timer(.3, lambda: f.publish(COMPLETE, 33))
        timer.start()
        cap = capture(SESSION, f.url, f.launch, f.nonce, OUT / 'bounded-success')
        timer.join()
        assert cap['status'] == 'qualified_screenshot_for_operator_review', cap
        assert cap['before_eval']['before']['png_sha256'] == MENU_SHA
        assert f.counts['key'] == f.counts['confirm'] == 0
        record('new_capture_qualified_historical_PNG', {'status': cap['status'],
             'screenshot_sha256': cap['screenshot_file_sha256'],
             'waited_ms': cap['before_eval']['waited_ms'], 'counts': dict(f.counts)})

        old_receipt = operate(SESSION, f.url, f.launch, f.nonce, 1, MENU_SHA,
                              'offline fixture target only', OUT / 'old-confirm.json',
                              source=OLD['confirm'])
        assert old_receipt['status'] == 'refused' and f.counts['confirm'] == 0
        assert 'PAGE_or_original_confirm_handler_fingerprint' in str(old_receipt)
        record('old_explicit_rejected_new_PAGE', {'status': old_receipt['status'],
                                                   'counts': dict(f.counts)})

        # This is scripted fixture approval, not a human viewing a VM frame.
        confirmed = operate(SESSION, f.url, f.launch, f.nonce, 1, MENU_SHA,
                            'offline fixture target only', OUT / 'new-confirm.json')
        assert confirmed['status'] == 'confirmed_and_cancelled', confirmed
        assert f.counts['confirm'] == 1 and f.counts['key'] == f.counts['stop'] == 0
        assert f.state.review_confirmation['guest_input_written'] is False
        status = js('window.__fx3InteractionDeadlineV1.status()')
        assert status['current']['state'] == 'cancelled'
        assert status['current']['due_ms'] == armed['current']['due_ms']
        record('new_explicit_confirm_cancelled', {'status': confirmed['status'],
              'guest_input_written': f.state.review_confirmation['guest_input_written'],
              'counts': dict(f.counts), 'deadline_state': status['current']['state'],
              'due_ms': status['current']['due_ms']})
    finally:
        f.close()

    bad = Fixture('tampered-page')
    try:
        bad.install()
        bad.arm()
        js('document.scripts[0].textContent += "\\n//fixture PAGE tamper"; true')
        invalid_capture = js((OPS / 'bounded_capture.js').read_text() + '(' + json.dumps({
            'url': bad.url, 'launch_id': bad.launch, 'nonce': bad.nonce,
            'step': 1, 'reference_sha': MENU_SHA}) + ')')
        assert invalid_capture['status'] == 'no_qualified_screenshot'
        assert 'PAGE_fingerprint' in invalid_capture['reason']
        bad.publish(COMPLETE, 33)
        wait(lambda: js('shownSHA') == MENU_SHA, 'complete fixture image')
        invalid_confirm = operate(SESSION, bad.url, bad.launch, bad.nonce, 1, MENU_SHA,
                                  'offline fixture target only', OUT / 'wrong-page-confirm.json')
        assert invalid_confirm['status'] == 'refused' and bad.counts['confirm'] == 0
        record('wrong_PAGE_rejected_by_capture_and_explicit', {
            'capture': invalid_capture['reason'], 'explicit': invalid_confirm['status'],
            'counts': dict(bad.counts)})
    finally:
        bad.close()

    new_bad = Fixture('wrong-deadline-page')
    try:
        js('document.scripts[0].textContent += "\\n//fixture PAGE tamper"; true')
        error = browser('eval', '--stdin', source=(OPS / 'deadline.js').read_text() + '(' + json.dumps({
            'expectedURL': new_bad.url, 'expectedLaunchId': new_bad.launch}) + ')', expect_error=True)
        assert 'PAGE fingerprint' in error and new_bad.counts['key'] == new_bad.counts['confirm'] == 0
        record('wrong_PAGE_rejected_by_deadline', {'error': error[-300:], 'counts': dict(new_bad.counts)})
    finally:
        new_bad.close()

    RESULT['passed'] = True


if __name__ == '__main__':
    try:
        run()
    finally:
        try:
            browser('close')
            RESULT['browser_closed'] = True
        except Exception as exc:
            RESULT['browser_close_error'] = repr(exc)
        (OUT / 'RESULT.json').write_text(json.dumps(RESULT, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': RESULT.get('passed'), 'cases': list(RESULT['cases']),
                      'browser_closed': RESULT.get('browser_closed')}, ensure_ascii=False))
