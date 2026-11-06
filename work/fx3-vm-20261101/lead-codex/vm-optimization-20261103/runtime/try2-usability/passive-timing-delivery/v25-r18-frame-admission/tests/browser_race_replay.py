"""Offline Chrome replay of the real PAGE and TrialState with controlled frames."""
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R11 = ROOT.parent / 'v25-r11-visible-rejection'
R12 = ROOT.parent / 'v25-r12-confirmation-progress' / 'trial_web_v22_navigation_review.py'
HARNESS = ROOT / 'tests' / 'race_harness.py'
OUT = ROOT / 'evidence' / ('run-' + str(int(time.time() * 1000)))
OUT.mkdir(exist_ok=True)
SESSION = 'fx3-r18-frame-admission-' + str(int(time.time()))
RESULT = {'scope': 'offline real Chrome plus TrialState/PAGE; no QEMU', 'cases': {}}


def browser(*args, stdin=None):
    p = subprocess.run(['agent-browser', '--session', SESSION, *args], input=stdin,
                       text=True, capture_output=True, timeout=30)
    if p.returncode:
        raise AssertionError(f'agent-browser {args}: {p.stdout} {p.stderr}')
    return p.stdout.strip()


def evaluate(js):
    return json.loads(browser('eval', '--stdin', stdin=js))


def page():
    return evaluate('''({
      displayed, shownSHA, displayedGeneration,
      statusSequence:lastStatus?.frame?.sequence,
      statusGeneration:lastStatus?.frame?.content_generation,
      statusSHA:lastStatus?.frame?.PNG_sha256,
      statusReady:lastStatus?.ready,
      menuDisabled:document.querySelector('[data-key="427"]').disabled,
      summary:document.querySelector('#failure-summary').textContent,
      detail:document.querySelector('#error').textContent,
      diagnosticsHidden:document.querySelector('#diagnostics').hidden,
      frameLoaded:image.complete&&image.naturalWidth>0,
      deliveryUnknown, awaitingStep,
      startDisabled:document.querySelector('#start').disabled
    })''')


def control(url, path, data=None):
    if data is None:
        with urllib.request.urlopen(url + '/' + path, timeout=3) as f:
            return json.load(f)
    req = urllib.request.Request(url + '/' + path, data=json.dumps(data).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=3) as f:
        return json.load(f)


def wait_for(predicate, reason, timeout=6):
    until = time.monotonic() + timeout
    last = None
    while time.monotonic() < until:
        last = page()
        if predicate(last):
            return last
        time.sleep(.05)
    raise AssertionError(f'{reason}: {last}')


def start(module, tag):
    ready = OUT / (tag + '-ready.json')
    ready.unlink(missing_ok=True)
    p = subprocess.Popen([sys.executable, '-u', str(HARNESS), '--module', str(module),
                          '--ready-file', str(ready)], stdout=subprocess.DEVNULL,
                         stderr=subprocess.PIPE, text=True)
    until = time.monotonic() + 5
    while not ready.exists() and time.monotonic() < until:
        if p.poll() is not None:
            raise AssertionError(p.stderr.read())
        time.sleep(.03)
    assert ready.exists(), 'harness readiness timeout'
    return p, json.loads(ready.read_text())


def reset(urls):
    control(urls['control'], 'reset', {})
    browser('open', urls['web'])
    return wait_for(lambda x: x['displayed'] == 1 and not x['menuDisabled'], 'initial A')


def save(name, urls):
    png = OUT / (name + '.png')
    browser('screenshot', str(png))
    RESULT['cases'][name] = {'page': page(), 'server': control(urls['control'], 'stats'),
                             'screenshot': png.name, 'screenshot_sha256': hashlib.sha256(png.read_bytes()).hexdigest()}
    return RESULT['cases'][name]


def click():
    browser('click', 'button[data-key="427"]')


def delay_frames():
    evaluate('''(() => {
      const original=window.fetch.bind(window);
      window.fetch=(url,options) => String(url).includes('/frame.png')
        ? new Promise((resolve,reject)=>setTimeout(()=>original(url,options).then(resolve,reject),2200))
        : original(url,options);
      return {testOnlyFrameDelayMs:2200};
    })()''')


def run():
    baseline, bu = start(R12, 'baseline')
    candidate, cu = start(ROOT / 'trial_web_v22_navigation_review.py', 'candidate')
    try:
        # Same image and generation: server advances to sequence 2 only after
        # the page clicked its displayed sequence 1.
        reset(cu)
        control(cu['control'], 'mode', {'mode': 'same_content_advance'})
        click()
        wait_for(lambda x: x['awaitingStep'] is None and x['menuDisabled'],
                 'accepted same-image key')
        same = save('same-content-sequence-accepted', cu)
        assert same['server']['requests']['key'] == same['server']['enqueued'] == 1
        assert same['server']['submissions'][0]['observed_sequence'] == 1
        assert same['server']['submissions'][0]['current_before_submit']['sequence'] == 2
        assert same['server']['submissions'][0]['current_before_submit']['generation'] == 1

        # A -> B between the visible image and TrialState.submit: exact 409.
        reset(cu)
        control(cu['control'], 'mode', {'mode': 'stale_sha'})
        click()
        wait_for(lambda x: '本次按键未被接收' in x['summary'] and x['displayedGeneration'] == 2
                 and not x['menuDisabled'], 'A to B rejection with new image loaded')
        switched = save('A-to-B-409-new-ready', cu)
        assert switched['server']['requests']['key'] == 1 and switched['server']['enqueued'] == 0
        assert not switched['page']['diagnosticsHidden']
        click()  # A second, explicit operator action; never automatic retry.
        wait_for(lambda x: x['summary'] == '' and x['awaitingStep'] is None, 'manual new-image key')
        manual = save('A-to-B-manual-second-click', cu)
        assert manual['server']['requests']['key'] == 2 and manual['server']['enqueued'] == 1

        # A -> B -> A returns to identical bytes, but generation changed.
        reset(cu)
        control(cu['control'], 'mode', {'mode': 'aba_generation'})
        click()
        wait_for(lambda x: '本次按键未被接收' in x['summary'] and x['displayedGeneration'] == 3,
                 'ABA generation rejection')
        aba = save('A-B-A-generation-409', cu)
        assert aba['page']['shownSHA'] == same['page']['shownSHA']
        assert aba['server']['requests']['key'] == 1 and aba['server']['enqueued'] == 0

        # A status can arrive before a new PNG finishes loading. Baseline leaves
        # the old enabled button visible during showFrame; candidate locks it.
        reset(bu)
        delay_frames()
        control(bu['control'], 'publish', {'color': 'B'})
        wait_for(lambda x: x['statusSequence'] == 2 and x['displayed'] == 1,
                 'baseline status B while image A displayed', timeout=2)
        old = save('baseline-loading-old-button-enabled', bu)
        assert old['page']['menuDisabled'] is False
        click()
        wait_for(lambda x: '本次按键未被接收' in x['summary'], 'baseline loading 409', timeout=5)
        old_after = save('baseline-loading-click-409', bu)
        assert old_after['server']['requests']['key'] == 1 and old_after['server']['enqueued'] == 0

        reset(cu)
        delay_frames()
        control(cu['control'], 'publish', {'color': 'B'})
        wait_for(lambda x: x['statusSequence'] == 2 and x['displayed'] == 1,
                 'candidate status B while image A displayed', timeout=2)
        locked = save('candidate-loading-button-locked', cu)
        assert locked['page']['menuDisabled'] is True
        assert locked['server']['requests']['key'] == locked['server']['enqueued'] == 0
        wait_for(lambda x: x['displayed'] == 2 and not x['menuDisabled'], 'new B loaded', timeout=5)
        fresh = save('candidate-loaded-new-frame-ready', cu)
        assert fresh['page']['frameLoaded']

        # Delivery unknown must remain locked and never cause a retry.
        reset(cu)
        control(cu['control'], 'mode', {'mode': 'http500'})
        click()
        wait_for(lambda x: x['deliveryUnknown'] and x['menuDisabled'], '500 unknown lock')
        time.sleep(.5)  # Cross one ordinary 400ms status tick.
        unknown = save('candidate-500-unknown-locked', cu)
        assert unknown['server']['requests']['key'] == 1 and unknown['server']['enqueued'] == 0

        # Startup has no frame by design. A visual-only lock must not disable
        # the original Start lifecycle control after browser-ready handshake.
        control(cu['control'], 'awaiting-launch', {})
        browser('open', cu['web'])
        wait_for(lambda x: not x['startDisabled'] and x['displayed'] == 0,
                 'browser-ready Start without a frame')
        before_start = save('candidate-no-frame-start-enabled', cu)
        assert before_start['server']['browser_ready'] is True
        browser('scrollintoview', '#start')
        browser('click', '#start')
        wait_for(lambda x: control(cu['control'], 'stats')['launch_request_id'] is not None,
                 'real PAGE Start POST accepted')
        after_start = save('candidate-no-frame-start-post', cu)
        assert after_start['server']['launch_request_id'] is not None
        assert after_start['server']['requests']['key'] == 0
        RESULT['passed'] = True
    finally:
        try:
            browser('close')
        finally:
            for p in (baseline, candidate):
                p.terminate()
                p.wait(timeout=5)
    RESULT['browser_closed'] = True
    RESULT['fixture_pids_exited'] = [p.poll() is not None for p in (baseline,candidate)]
    (OUT / 'RESULT.json').write_text(json.dumps(RESULT, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': RESULT['passed'], 'cases': list(RESULT['cases']),
                      'browser_closed': RESULT['browser_closed'],
                      'fixture_pids_exited': RESULT['fixture_pids_exited']}, ensure_ascii=False))


if __name__ == '__main__':
    run()
