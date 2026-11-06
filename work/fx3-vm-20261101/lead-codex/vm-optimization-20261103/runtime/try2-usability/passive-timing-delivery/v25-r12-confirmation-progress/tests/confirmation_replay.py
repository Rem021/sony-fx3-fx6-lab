"""Real Chrome replay of r11/r12 PAGE against actual TrialState; loopback only, no QEMU."""
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / 'v25-r11-visible-rejection' / 'trial_web_v22_navigation_review.py'
CANDIDATE = ROOT / 'trial_web_v22_navigation_review.py'
EVIDENCE = ROOT / 'tests' / 'confirmation-evidence'
EVIDENCE.mkdir(exist_ok=True)
SESSION = 'fx3-r12-confirm-' + str(int(time.time()))
results = {}


def browser(*args, stdin=None):
    r = subprocess.run(['agent-browser', '--session', SESSION, *args], input=stdin,
                       text=True, capture_output=True, timeout=30)
    if r.returncode:
        raise AssertionError(f'browser {args}: {r.stdout} {r.stderr}')
    return r.stdout


def dom():
    return json.loads(browser('eval', '--stdin', stdin='''({
      summary:document.querySelector('#failure-summary').textContent,
      diagnosticsHidden:document.querySelector('#diagnostics').hidden,
      menuDisabled:document.querySelector('[data-key="427"]').disabled,
      confirmDisabled:document.querySelector('#confirm').disabled,
      status:document.querySelector('#status').textContent,
      meta:document.querySelector('#meta').textContent,
      displayed, shownSHA, displayedGeneration, reviewAwaiting, reviewUnknown,
      pendingConfirm:pendingConfirm&&{request_id:pendingConfirm.request_id,step:pendingConfirm.step,
        observed_sequence:pendingConfirm.observed_sequence,content_generation:pendingConfirm.content_generation,
        PNG_sha256:pendingConfirm.PNG_sha256}
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
    return await_condition(lambda x: not x['menuDisabled'] and x['displayed'] > 0,
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


def completed_confirm_response(request_id):
    """Read Chrome's completed network body; never persist authorization headers."""
    listing = json.loads(browser('network', 'requests', '--filter', 'confirm-visual', '--json'))
    for item in listing.get('data', {}).get('requests', []):
        detail = json.loads(browser('network', 'request', str(item['requestId']), '--json'))
        d = detail.get('data', {})
        try:
            posted = json.loads(d.get('postData', '{}'))
            response = json.loads(d.get('responseBody', '{}'))
        except (ValueError, TypeError):
            continue
        if posted.get('request_id') == request_id and response.get('request_id') == request_id:
            return {'request_id': request_id, 'status': d.get('status'),
                    'confirmed': response.get('confirmed'),
                    'guest_input_written': response.get('guest_input_written')}
    return None


def start_review(urls):
    click_key()
    await_condition(lambda x: not x['confirmDisabled'] and
                    control(urls['control'], 'stats')['requests']['key'] == 1,
                    'key received and review pending')


def baseline(urls):
    reset_page(urls)
    start_review(urls)
    control(urls['control'], 'mode', {'mode': 'confirm_then_b'})
    click_confirm()
    await_condition(lambda x: x['displayed'] == 2 and x['reviewAwaiting'] and
                    x['menuDisabled'] and not control(urls['control'], 'stats')['review_required'],
                    'r11 stuck after HTTP 200 historical confirmation and new B frame')
    time.sleep(.9)
    x = save('r11-confirm-200-new-frame-stuck', urls)
    assert x['stats']['requests'] == {'key': 1, 'confirm': 1}
    assert x['stats']['enqueued'] == 1 and x['browser']['pendingConfirm']


def candidate(urls):
    reset_page(urls)
    start_review(urls)
    control(urls['control'], 'mode', {'mode': 'confirm_then_b'})
    click_confirm()
    await_condition(lambda x: x['displayed'] == 2 and not x['menuDisabled'] and
                    not x['reviewAwaiting'] and not x['pendingConfirm'],
                    'r12 HTTP 200 historical confirmation then new B loaded')
    x = save('r12-confirm-200-new-frame-unlocked', urls)
    assert x['stats']['requests'] == {'key': 1, 'confirm': 1} and x['stats']['enqueued'] == 1
    assert x['browser']['displayedGeneration'] == 2
    click_key()  # Explicit automated browser click, observed B frame; no auto resend.
    await_condition(lambda x: not x['confirmDisabled'] and
                    control(urls['control'], 'stats')['requests']['key'] == 2,
                    'second manual key after new B frame')
    x = save('r12-manual-key-after-B', urls)
    assert x['stats']['enqueued'] == 2 and x['stats']['key_bodies'][-1]['observed_sequence'] == 2
    assert x['stats']['requests']['confirm'] == 1

    reset_page(urls)
    start_review(urls)
    control(urls['control'], 'mode', {'mode': 'confirm_then_aba'})
    click_confirm()
    await_condition(lambda x: x['displayed'] == 3 and x['displayedGeneration'] == 3 and
                    not x['menuDisabled'] and not x['reviewAwaiting'],
                    'A confirmed then B to A with newer generation')
    x = save('r12-confirm-200-ABA-generation', urls)
    assert x['stats']['requests'] == {'key': 1, 'confirm': 1} and x['stats']['enqueued'] == 1
    assert x['stats']['confirm_bodies'][0]['content_generation'] == 1
    assert x['browser']['displayedGeneration'] == 3
    click_key()
    await_condition(lambda x: control(urls['control'], 'stats')['enqueued'] == 2 and
                    not x['confirmDisabled'], 'manual key on ABA generation 3')
    x = save('r12-manual-key-after-ABA', urls)
    assert x['stats']['key_bodies'][-1]['observed_sequence'] == 3
    assert x['stats']['requests']['confirm'] == 1

    reset_page(urls)
    start_review(urls)
    control(urls['control'], 'mode', {'mode': 'confirm_lost_then_b'})
    click_confirm()
    await_condition(lambda x: x['displayed'] == 2 and x['reviewAwaiting'] and x['menuDisabled'],
                    'lost response with initially mismatched status receipt')
    control(urls['control'], 'tamper-confirmation', {'request_id': 'wrong-nonce'})
    for field, wrong in [('request_id', 'wrong-nonce'), ('step', 99),
                         ('observed_sequence', 99), ('content_generation', 99),
                         ('PNG_sha256', '0'*64), ('guest_input_written', True)]:
        control(urls['control'], 'tamper-confirmation', {field: wrong})
        time.sleep(.6)
        x = dom()
        assert x['menuDisabled'] and x['reviewAwaiting'] and x['pendingConfirm'], (field, x)
        results['mismatch-' + field] = {'browser': x, 'stats': control(urls['control'], 'stats')}
    # Wait through the fetch deadline: unknown delivery must remain locked.
    await_condition(lambda x: x['reviewUnknown'] and x['menuDisabled'], 'lost response unknown locked', timeout=11)
    x = save('r12-lost-confirm-unknown-locked', urls)
    assert x['stats']['requests'] == {'key': 1, 'confirm': 1} and x['stats']['enqueued'] == 1
    control(urls['control'], 'restore-confirmation')
    await_condition(lambda x: x['displayed'] == 2 and not x['menuDisabled'] and
                    not x['reviewUnknown'] and not x['pendingConfirm'],
                    'exact historical status receipt unlocks only after B loaded')
    x = save('r12-lost-confirm-status-match-new-frame', urls)
    assert x['stats']['requests'] == {'key': 1, 'confirm': 1} and x['stats']['enqueued'] == 1
    click_key()
    await_condition(lambda x: control(urls['control'], 'stats')['enqueued'] == 2 and
                    not x['confirmDisabled'], 'manual key after recovered confirmation')
    x = save('r12-manual-key-after-lost-confirm', urls)
    assert x['stats']['key_bodies'][-1]['observed_sequence'] == 2
    assert x['stats']['requests'] == {'key': 2, 'confirm': 1}

    # A prior receipt cannot discharge a new confirmation request.
    control(urls['control'], 'mode', {'mode': 'confirm_lost_then_b'})
    click_confirm()
    await_condition(lambda x: x['reviewAwaiting'] and x['menuDisabled'], 'second confirmation pending')
    control(urls['control'], 'previous-confirmation')
    time.sleep(.7)
    x = save('r12-old-receipt-does-not-unlock-new-request', urls)
    assert x['browser']['reviewAwaiting'] and x['browser']['menuDisabled']
    assert x['stats']['requests']['confirm'] == 2 and x['stats']['enqueued'] == 2
    control(urls['control'], 'restore-confirmation')
    await_condition(lambda x: not x['menuDisabled'] and not x['reviewAwaiting'],
                    'matching second receipt unlocks')
    save('r12-second-matching-receipt', urls)

    # The first ACK can arrive after status unlocked it and a second request began.
    reset_page(urls)
    start_review(urls)
    control(urls['control'], 'mode', {'mode': 'confirm_delayed_ack_then_b'})
    click_confirm()
    await_condition(lambda x: x['displayed'] == 2 and not x['menuDisabled'],
                    'first confirmation matched through status while ACK delayed')
    click_key()
    await_condition(lambda x: not x['confirmDisabled'] and
                    control(urls['control'], 'stats')['enqueued'] == 2,
                    'second key awaiting its own confirmation')
    control(urls['control'], 'mode', {'mode': 'confirm_lost_then_b'})
    click_confirm()
    await_condition(lambda x: x['reviewAwaiting'] and x['menuDisabled'] and
                    x['pendingConfirm'], 'second request pending')
    control(urls['control'], 'previous-confirmation')
    await_condition(lambda x: len(control(urls['control'], 'stats')['delayed_ack_sent']) == 1,
                    'first delayed HTTP ACK actually returned', timeout=10)
    prior_stats = control(urls['control'], 'stats')
    old_id = prior_stats['confirm_bodies'][0]['request_id']
    await_condition(lambda _: completed_confirm_response(old_id) is not None,
                    'Chrome received completed old confirmation response', timeout=5)
    results['late_old_http_response'] = completed_confirm_response(old_id)
    assert results['late_old_http_response']['status'] == 200
    assert results['late_old_http_response']['confirmed'] is True
    assert results['late_old_http_response']['guest_input_written'] is False
    time.sleep(.5)  # Let the old response's JS continuation run before the DOM receipt.
    x = save('r12-late-old-ack-keeps-new-request-locked', urls)
    assert x['browser']['reviewAwaiting'] and x['browser']['menuDisabled']
    assert x['browser']['pendingConfirm']['request_id'] == x['stats']['confirm_bodies'][1]['request_id']
    assert x['stats']['requests'] == {'key': 2, 'confirm': 2} and x['stats']['enqueued'] == 2
    assert x['stats']['delayed_ack_sent'] == [old_id]
    results['late_old_http_and_pending_dom'] = {'http': results['late_old_http_response'],
                                               'dom': x['browser'], 'requests': x['stats']['requests']}
    control(urls['control'], 'restore-confirmation')
    await_condition(lambda x: not x['menuDisabled'] and not x['reviewAwaiting'],
                    'second request still requires its own exact receipt')
    save('r12-late-old-ack-new-receipt-matched', urls)

    reset_page(urls)
    start_review(urls)
    control(urls['control'], 'mode', {'mode': 'confirm_delayed_ack_then_b'})
    click_confirm()
    await_condition(lambda x: x['displayed'] == 2 and not x['menuDisabled'],
                    'first delayed ACK pending, status already matched')
    click_key()
    await_condition(lambda x: not x['confirmDisabled'], 'second review for 409 case')
    control(urls['control'], 'mode', {'mode': 'confirm_stale'})
    click_confirm()
    await_condition(lambda x: '本次画面确认未被接收' in x['summary'] and not x['confirmDisabled'],
                    'second confirmation explicitly rejected')
    await_condition(lambda x: len(control(urls['control'], 'stats')['delayed_ack_sent']) == 1,
                    'first delayed ACK returned after second rejection', timeout=10)
    prior_stats = control(urls['control'], 'stats')
    old_id = prior_stats['confirm_bodies'][0]['request_id']
    await_condition(lambda _: completed_confirm_response(old_id) is not None,
                    'Chrome received old HTTP ACK after new rejection', timeout=5)
    results['late_old_http_response_after_rejection'] = completed_confirm_response(old_id)
    assert results['late_old_http_response_after_rejection']['status'] == 200
    time.sleep(.5)
    x = save('r12-late-old-ack-keeps-new-rejection', urls)
    assert '本次画面确认未被接收' in x['browser']['summary']
    assert x['stats']['requests'] == {'key': 2, 'confirm': 2} and x['stats']['enqueued'] == 2
    results['late_old_http_and_rejection_dom'] = {'http': results['late_old_http_response_after_rejection'],
                                                  'dom': x['browser'], 'requests': x['stats']['requests']}


try:
    for tag, module, test in [('baseline', BASE, baseline), ('candidate', CANDIDATE, candidate)]:
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
print('CONFIRMATION_BROWSER_PASS', len([x for x in results.values() if isinstance(x, dict) and x.get('screenshot')]),
      'screenshots', EVIDENCE / 'RESULT.json')
