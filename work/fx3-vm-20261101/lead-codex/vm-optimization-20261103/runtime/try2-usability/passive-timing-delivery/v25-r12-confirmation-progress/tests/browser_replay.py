"""Real Chrome/agent-browser replay against local TrialState pages; no QEMU."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / 'v25-r10-independent-diagnostics' / 'trial_web_v22_navigation_review.py'
CANDIDATE = ROOT / 'trial_web_v22_navigation_review.py'
EVIDENCE = ROOT / 'tests' / 'browser-evidence'
EVIDENCE.mkdir(exist_ok=True)
SESSION = 'fx3-r11-fixture-' + str(int(time.time()))
results = {}
options = argparse.ArgumentParser()
options.add_argument('--candidate-only', action='store_true')
options = options.parse_args()
if options.candidate_only and (EVIDENCE / 'RESULT.json').exists():
    previous = json.loads((EVIDENCE / 'RESULT.json').read_text())
    if 'r10-swallowed-409' in previous:
        results['r10-swallowed-409'] = previous['r10-swallowed-409']


def browser(*args, stdin=None):
    r = subprocess.run(['agent-browser', '--session', SESSION, *args], input=stdin,
                       text=True, capture_output=True, timeout=30)
    if r.returncode:
        raise AssertionError(f'browser {args}: {r.stdout} {r.stderr}')
    return r.stdout


def dom():
    return json.loads(browser('eval', '--stdin', stdin='''({
      summary:document.querySelector('#failure-summary').textContent,
      detail:document.querySelector('#error').textContent,
      diagnosticsHidden:document.querySelector('#diagnostics').hidden,
      menuDisabled:document.querySelector('[data-key="427"]').disabled,
      confirmDisabled:document.querySelector('#confirm').disabled,
      status:document.querySelector('#status').textContent,
      meta:document.querySelector('#meta').textContent
    })'''))


def control(url, action, body=None):
    if action == 'stats':
        with urllib.request.urlopen(url + '/stats', timeout=3) as r:
            return json.load(r)
    request = urllib.request.Request(url + '/' + action,
        data=json.dumps(body or {}).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=3) as r:
        return json.load(r)


def await_condition(predicate, why, timeout=12):
    end = time.monotonic() + timeout
    last = None
    while time.monotonic() < end:
        last = dom()
        if predicate(last):
            return last
        time.sleep(.2)
    raise AssertionError(f'timed out waiting for {why}: {last}')


def start_harness(module, tag):
    ready = EVIDENCE / (tag + '-ready.json')
    ready.unlink(missing_ok=True)
    p = subprocess.Popen([sys.executable, '-u', str(ROOT / 'tests' / 'rejection_harness.py'),
                          '--module', str(module), '--ready-file', str(ready)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    end = time.monotonic() + 5
    while not ready.exists() and time.monotonic() < end:
        if p.poll() is not None:
            raise AssertionError('fixture exited: ' + p.stderr.read())
        time.sleep(.05)
    if not ready.exists():
        p.terminate()
        raise AssertionError('fixture did not start')
    return p, json.loads(ready.read_text())


def reset_page(urls):
    control(urls['control'], 'reset')
    browser('open', urls['web'])
    return await_condition(lambda x: not x['menuDisabled'] and x['meta'].find('提交帧') >= 0,
                           'valid initial frame')


def save(name, urls):
    path = EVIDENCE / (name + '.png')
    browser('screenshot', str(path))
    results[name] = {'browser': dom(), 'stats': control(urls['control'], 'stats'),
                     'screenshot': str(path), 'screenshot_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    return results[name]


def click_key():
    browser('click', 'button[data-key="427"]')


def click_confirm():
    browser('click', '#confirm')


def test_baseline(urls):
    reset_page(urls)
    control(urls['control'], 'mode', {'mode': 'stale_sha'})
    click_key()
    time.sleep(1.2)  # Cross at least one 400 ms status tick after the 409 response.
    x = save('r10-swallowed-409', urls)
    assert x['browser']['summary'] == '' and x['browser']['diagnosticsHidden']
    assert x['stats']['requests']['key'] == 1 and x['stats']['enqueued'] == 0


def test_candidate(urls):
    reset_page(urls)
    control(urls['control'], 'mode', {'mode': 'stale_sha'})
    click_key()
    await_condition(lambda x: '本次按键未被接收' in x['summary'] and
                    not x['menuDisabled'] and '提交帧 2' in x['meta'],
                    'visible key 409 plus freshly loaded frame')
    x = save('r11-stale-409-visible', urls)
    assert x['stats']['requests']['key'] == 1 and x['stats']['enqueued'] == 0
    assert not x['browser']['menuDisabled'] and not x['browser']['diagnosticsHidden']
    click_key()  # Deliberate user action after the newly displayed frame, never a retry loop.
    await_condition(lambda x: x['summary'] == '' and not x['confirmDisabled'], 'successful manual key')
    x = save('r11-manual-key-accepted', urls)
    assert x['stats']['requests']['key'] == 2 and x['stats']['enqueued'] == 1

    control(urls['control'], 'mode', {'mode': 'confirm_stale'})
    click_confirm()
    await_condition(lambda x: '本次画面确认未被接收' in x['summary'] and
                    not x['confirmDisabled'] and '提交帧 3' in x['meta'],
                    'visible confirm 409 plus freshly loaded frame')
    x = save('r11-confirm-409-visible', urls)
    assert x['stats']['requests']['confirm'] == 1 and x['stats']['review_required']
    click_confirm()
    await_condition(lambda x: x['summary'] == '' and x['confirmDisabled'], 'successful manual confirm')
    x = save('r11-manual-confirm-accepted', urls)
    assert x['stats']['requests']['confirm'] == 2 and not x['stats']['review_required']
    assert x['stats']['enqueued'] == 1

    reset_page(urls)
    control(urls['control'], 'mode', {'mode': 'aba_generation'})
    click_key()
    await_condition(lambda x: '本次按键未被接收' in x['summary'], 'ABA generation rejection')
    x = save('r11-aba-generation-409', urls)
    assert x['stats']['content_generation'] == 3 and x['stats']['enqueued'] == 0

    reset_page(urls)
    control(urls['control'], 'mode', {'mode': 'http500'})
    click_key()
    await_condition(lambda x: '按键是否送达尚未确认' in x['summary'], '500 unknown')
    x = save('r11-http500-unknown-locked', urls)
    assert x['browser']['menuDisabled'] and x['stats']['enqueued'] == 0

    reset_page(urls)
    control(urls['control'], 'mode', {'mode': 'invalid_json'})
    click_key()
    await_condition(lambda x: '按键是否送达尚未确认' in x['summary'], 'invalid JSON unknown')
    x = save('r11-invalid-json-unknown-locked', urls)
    assert x['browser']['menuDisabled'] and x['stats']['enqueued'] == 0
    # Prove the fixture returns invalid raw bytes, not a JSON-encoded string.
    control(urls['control'], 'reset')
    control(urls['control'], 'mode', {'mode': 'invalid_json'})
    page = urllib.request.urlopen(urls['web'], timeout=3).read().decode()
    token = json.loads(re.search(r'const token=(.*?);', page).group(1))
    req = urllib.request.Request(urls['web'] + '/api/key',
        data=json.dumps({'key': 427, 'observed_sequence': 1}).encode(),
        headers={'X-Trial-Token': token, 'Content-Type': 'application/json', 'Origin': urls['web']})
    with urllib.request.urlopen(req, timeout=3) as response:
        raw = response.read()
        assert response.status == 202 and raw == b'not valid JSON'
    try:
        json.loads(raw)
        raise AssertionError('fixture unexpectedly returned valid JSON')
    except json.JSONDecodeError:
        pass
    results['invalid_json_raw'] = {'status': 202, 'raw_hex': raw.hex(),
                                   'stats': control(urls['control'], 'stats')}

    reset_page(urls)
    control(urls['control'], 'mode', {'mode': 'timeout'})
    click_key()
    await_condition(lambda x: '按键是否送达尚未确认' in x['summary'], 'timeout unknown', timeout=11)
    x = save('r11-timeout-unknown-locked', urls)
    assert x['browser']['menuDisabled'] and x['stats']['enqueued'] == 0

    reset_page(urls)
    click_key()
    await_condition(lambda x: not x['confirmDisabled'], 'review for lost-confirm case')
    control(urls['control'], 'mode', {'mode': 'confirm_stale'})
    click_confirm()
    await_condition(lambda x: '本次画面确认未被接收' in x['summary'] and
                    not x['confirmDisabled'], 'prior confirm 409 plus latest frame')
    control(urls['control'], 'mode', {'mode': 'confirm_response_lost'})
    click_confirm()
    await_condition(lambda x: x['summary'] == '' and x['confirmDisabled'] and
                    control(urls['control'], 'stats')['review_required'] is False,
                    'status-matched confirm success despite lost response')
    time.sleep(8.5)  # Let the earlier request's 8 s fetch deadline expire.
    x = save('r11-confirm-lost-response-status-match', urls)
    assert x['browser']['summary'] == '' and not x['browser']['menuDisabled']
    assert x['stats']['requests']['confirm'] == 2 and x['stats']['enqueued'] == 1

    reset_page(urls)
    control(urls['control'], 'mode', {'mode': 'stale_sha'})
    click_key()
    await_condition(lambda x: '本次按键未被接收' in x['summary'], 'prior 409 for terminal')
    control(urls['control'], 'terminal', {'phase': 'finished', 'error': 'native_model_power_off_observed test',
                                         'message': '离线原生终态'})
    await_condition(lambda x: '原生省电关机' in x['summary'] and '本次按键未被接收' not in x['summary'],
                    'native terminal authority')
    save('r11-native-terminal-priority', urls)

    reset_page(urls)
    control(urls['control'], 'publish', {'color': 'BAD'})
    await_condition(lambda x: '网页画面或状态读取失败' in x['summary'], 'render failure')
    assert dom()['menuDisabled']
    control(urls['control'], 'terminal', {'phase': 'finished', 'message': '离线已结束且资源回收'})
    await_condition(lambda x: '离线已结束且资源回收' in x['status'] and
                    x['summary'] == '' and x['diagnosticsHidden'], 'finished overrides old render fault')
    save('r11-finished-over-render-fault', urls)

    reset_page(urls)
    control(urls['control'], 'mode', {'mode': 'delayed_409'})
    click_key()
    control(urls['control'], 'publish', {'color': 'BAD'})
    await_condition(lambda x: '网页画面或状态读取失败' in x['summary'], 'render fault during key request')
    time.sleep(1.2)
    x = save('r11-render-fault-over-async-409', urls)
    assert '网页画面或状态读取失败' in x['browser']['summary'] and x['browser']['menuDisabled']


try:
    cases = [('candidate', CANDIDATE, test_candidate)] if options.candidate_only else [
        ('base', BASE, test_baseline), ('candidate', CANDIDATE, test_candidate)]
    for tag, module, test in cases:
        proc, urls = start_harness(module, tag)
        try:
            test(urls)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
    results['pass'] = True
finally:
    try:
        browser('close')
    except Exception:
        pass
    (EVIDENCE / 'RESULT.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
print('BROWSER_FIXTURE_PASS', len([x for x in results.values() if isinstance(x, dict) and x.get('screenshot')]),
      'screenshots', EVIDENCE / 'RESULT.json')
