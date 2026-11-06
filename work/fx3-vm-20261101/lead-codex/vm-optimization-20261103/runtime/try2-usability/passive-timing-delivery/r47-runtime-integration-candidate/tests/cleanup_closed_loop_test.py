#!/usr/bin/env python3
"""r47 cleanup closed loop: actual _cleanup_once -> actual certify -> seal/revalidate.

Fake browser/ev/dl/resource/native dependencies only. No real browser, PID probe,
QMP, VM or guest. The only writes are candidate run-inputs/receipts temp paths.
"""
import errno
import hashlib
import importlib
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RUN = HERE / 'run-inputs/r47-offline-closed-loop'
RECEIPTS = HERE / 'receipts'
RECEIPTS.mkdir(exist_ok=True)
URL = 'http://127.0.0.1:58245/'
LAUNCH = 'd23ffef6-215c-41a8-80b6-0da39ac31114'
NONCE = 'd1b0d0c4-0eff-4ca9-9c61-46c15384101c'
DOC = '70f5e6af-bcaf-4fdf-8177-520fff7a31a7'
ORIGIN = 1793877848674.9
RUNI = '9cab2340-e878-4c3a-8229-e10e989798fa'
SESSION = 'fx3-deadline-r47offline'
RUNNER = 53378
QEMU = 53782
RESULTS = []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def wj(p, v):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n')


def prepare_run():
    RUN.mkdir(parents=True, exist_ok=True)
    source = json.loads((HERE / 'SOURCE-FREEZE.json').read_text())
    plan = json.loads((HERE / 'NAVIGATION-PLAN.json').read_text())
    cfg = {'candidate_source_root': str(HERE), 'runner_profile': 'r47-runtime-integration-60s',
           'session': SESSION, 'frozen_root': str(HERE.parent / 'v25-r21-recovery-integration'),
           'task_id': 'task_r47offline', 'dispatch_id': 'ctx_r47offline',
           'scripted_navigation': True, 'visual_review_at_click': False,
           'plan_sha': hashlib.sha256((HERE / 'NAVIGATION-PLAN.json').read_bytes()).hexdigest(),
           'steps': plan['steps']}
    wj(RUN / 'config.json', cfg)
    wj(RUN / 'LOCAL-SOURCE-FREEZE.json', {str(HERE / rel): h for rel, h in source.items()})
    wj(RUN / 'ledger.json', {'attempts': [], 'recoveries': []})
    wj(RUN / 'trial-web-final-receipt.json', {'acknowledged': True})
    wj(RUN / 'current-attempt.json', {'step': 8, 'nonce': NONCE, 'attempt_id': 'att',
                                      'postkey_binding': {'document_id': DOC, 'document_time_origin': ORIGIN,
                                                          'run_incarnation': RUNI}})
    os.environ['FX3_NAV_RUN_DIR'] = str(RUN)
    sys.path.insert(0, str(HERE / 'runtime-wrapper'))
    cleanup = importlib.import_module('cleanup')
    ce = importlib.import_module('cleanup_evidence')
    return cleanup, ce


def armed_alarm(nonce=NONCE):
    return {'version': 1, 'deadline_ms': 60000, 'expectedURL': URL, 'expectedLaunchId': LAUNCH,
            'documentTimeOrigin': ORIGIN, 'sealed': False,
            'current': {'nonce': nonce, 'state': 'armed', 'armed_ms': 1000.0, 'due_ms': 61000.0,
                        'deadline_ms': 60000},
            'events': [{'event': 'installed', 'performance_ms': 10.0},
                       {'event': 'armed', 'nonce': nonce, 'due_ms': 61000.0, 'performance_ms': 1000.0}]}


def nonarmed_alarm():
    a = armed_alarm()
    a['current'] = {'nonce': NONCE, 'state': 'cancelled', 'armed_ms': 1000.0, 'due_ms': 61000.0,
                    'cancelled_ms': 3000.0, 'deadline_ms': 60000}
    a['events'] = [{'event': 'installed'}, {'event': 'armed', 'nonce': NONCE, 'due_ms': 61000.0},
                   {'event': 'cancelled', 'nonce': NONCE, 'elapsed_ms': 2000.0}]
    return a


def make_call(cleanup, ce, kind, after_active=False, dispose_ok=True, alarm=None):
    call = RUN / 'cleanup-calls' / str(uuid.uuid4())
    call.mkdir(parents=True)
    if alarm is None:
        alarm = armed_alarm() if kind == 'armed' else nonarmed_alarm()
    state = {'finished': True, 'ending': True, 'url': URL, 'document_id': DOC,
             'document_time_origin': ORIGIN, 'alarm': alarm,
             'lastStatus': {'phase': 'finished', 'launch_request_id': LAUNCH,
                            'run_incarnation': RUNI}}
    dispose = None
    if kind == 'nonarmed':
        dispose = {'version': 1, 'deadline_ms': 60000, 'expectedURL': URL, 'expectedLaunchId': LAUNCH,
                   'documentTimeOrigin': ORIGIN, 'sealed': True,
                   'current': dict(alarm['current']) if alarm.get('current') else None,
                   'events': list(alarm['events']) + [{'event': 'disposed', 'performance_ms': 4000.0}]}
    cleanup.write = lambda name, data: wj(call / name, data)
    cleanup.event = lambda *a, **k: None

    def ev(name, source):
        if name == 'End-original-button':
            out = {'End_invoked': True}
        elif name == 'ended-state':
            out = state
        else:
            raise RuntimeError('unexpected ev ' + name)
        wj(call / (name + '-process.json'), {'returncode': 0, 'stdout': json.dumps(out)})
        return out
    cleanup.ev = ev

    def browser(name, args, timeout=20):
        if name == 'ended-page':
            (call / 'ended-page.png').write_bytes(b'\x89PNG\r\n\x1a\n' + b'x' * 16)
            out = {}
        elif name == 'HAR-stop':
            wj(call / 'traffic.har', {'log': {'entries': []}})
            out = {}
        elif name == 'browser-before-close':
            out = {'success': True, 'data': {'session': SESSION, 'active': True, 'pid': 5555}}
        elif name == 'browser-after-close':
            out = {'success': True, 'data': {'session': SESSION, 'active': bool(after_active),
                                             'pid': 5555 if after_active else None}}
        elif name == 'browser-close':
            out = {}
        else:
            raise RuntimeError('unexpected browser ' + name)
        wj(call / (name + '-process.json'), {'returncode': 0, 'stdout': json.dumps(out)})
        return out
    cleanup.browser = browser

    def dl(name, action, nonce=None):
        if name == 'deadline-after-End':
            out = alarm
        elif name == 'deadline-dispose':
            if not dispose_ok:
                raise RuntimeError('synthetic dispose unavailable')
            out = dispose
        else:
            raise RuntimeError('unexpected dl ' + name)
        wj(call / (name + '-process.json'), {'returncode': 0, 'stdout': json.dumps(out)})
        return out
    cleanup.dl = dl

    class FakeOS:
        @staticmethod
        def kill(pid, sig):
            raise ProcessLookupError
    class FakeSock:
        def settimeout(self, x):
            pass
        def connect_ex(self, addr):
            return errno.ECONNREFUSED
        def close(self):
            pass
    class FakeSocket:
        def socket(self):
            return FakeSock()
    cleanup.os = FakeOS
    cleanup.socket = FakeSocket()
    c = {'url': URL, 'run': str(RUN), 'runner_pid': RUNNER, 'launch_id': LAUNCH}
    return call, c, alarm, state


def fake_native(ce):
    native = {'files': {}, 'qemu_pid': QEMU,
              'host_launch_uuid': 'b1f17b5a-4e34-4cb9-ba4b-d43838c36de9',
              'locks': ['/lock/a', '/lock/b'], 'scope': 'offline fake native/resource evidence'}

    def fn(cc, folder=None):
        if folder:
            folder.mkdir(exist_ok=True)
            for n in ('command.json', 'trial-session.json', 'receipt.json',
                      'trial-web-final-receipt.json', 'resource-guard-receipt.json'):
                wj(folder / n, {})
        return native
    ce.native_evidence = fn
    return native


def probe(c, q):
    return {'resources_closed': True, 'runner_pid': c['runner_pid'], 'qemu_pid': q,
            'runner_absent': True, 'qemu_absent': True, 'port_closed': True,
            'locks': [{'path': '/lock/a', 'free_at_probe': True},
                      {'path': '/lock/b', 'free_at_probe': True}], 'errors': []}


def complete_and_revalidate(ce, call, c, cfg):
    body = json.loads((call / 'body-result.json').read_text())
    proof = ce.certify(call, c, cfg, body, probe)
    wj(call / 'proof.json', proof)
    binding = {'candidate_run_dir': str(RUN), 'session': SESSION, 'task_id': 't', 'dispatch_id': 'd',
               'source_root': str(HERE), 'profile': 'r47-runtime-integration-60s',
               'source_sha256': 'a' * 64, 'core_sha256': 'b' * 64, 'config_sha256': 'c' * 64,
               'runtime_sha256': 'd' * 64, 'local_freeze_sha256': 'e' * 64,
               'runtime': c}
    wj(call / 'invocation.json', {'schema': ce.SCHEMA, 'call_id': call.name,
                                  'binding': binding, 'owner': True})
    value = {'schema': ce.SCHEMA, 'call_id': call.name, 'status': 'completed', 'errors': [],
             'binding': binding, 'resources': proof['resources'], 'original_action_outcome': 'unchanged'}
    wj(call / 'result.json', value)
    (call / 'stdout.txt').write_text('{}\n')
    (call / 'stderr.txt').write_text('')
    public = json.dumps(value, ensure_ascii=False) + '\n'
    (call / 'return.stdout.txt').write_text(public)
    wj(call / 'RETURN-HASH.json', {'sha256': hashlib.sha256(public.encode()).hexdigest(),
                                   'bytes': len(public.encode()), 'scope': 'offline test exact stdout'})
    ref = ce.seal(call)
    call2, value2 = ce.validate_reference(RUN, ref)
    rev = ce.revalidate(RUN, ref, binding, c, cfg, probe)
    assert call2 == call and value2['status'] == 'completed'
    return proof, ref, rev


def record(name, detail):
    RESULTS.append({'case': name, 'passed': True, **detail})
    print('PASS', name)


def main():
    cleanup, ce = prepare_run()
    native = fake_native(ce)
    cfg = {'session': SESSION}

    # 1. Armed full closed loop: actual _cleanup_once -> certify -> seal/reference -> revalidate.
    call, c, alarm, state = make_call(cleanup, ce, 'armed')
    body = cleanup._cleanup_once(c, call)
    assert body['alarm_disposition'] == 'valid_armed_do_not_cancel_or_dispose'
    assert body['errors'] == [] and body['runner_alive'] is False and body['port_closed'] is True
    assert (call / 'dispose-not-invoked.json').is_file() and not (call / 'deadline-dispose.json').exists()
    proof, ref, rev = complete_and_revalidate(ce, call, c, cfg)
    assert proof['alarm']['dispose_invoked'] is False
    assert proof['alarm']['nonce'] == NONCE and proof['alarm']['due_ms'] == 61000.0
    assert proof['ended_state']['End_invoked'] is True
    assert proof['browser'] == {'session': SESSION, 'before_pid': 5555, 'after_active': False, 'after_pid': None}
    assert rev['resources']['resources_closed'] is True
    record('armed_actual_cleanup_once_certify_seal_revalidate',
           {'body': {k: body[k] for k in ('alarm_disposition', 'errors', 'runner_alive', 'port_closed')},
            'proof_alarm': proof['alarm'], 'seal_receipt': ref['call_id'],
            'revalidated': True, 'actual_cleanup_once': True, 'real_browser_used': False,
            'pid_probe_used': False})

    # 2. Nonarmed full closed loop: actual dispose path required and revalidated.
    call, c, alarm, state = make_call(cleanup, ce, 'nonarmed')
    body = cleanup._cleanup_once(c, call)
    assert body['alarm_disposition'] == 'valid_nonarmed' and body['errors'] == []
    assert (call / 'deadline-dispose.json').is_file() and not (call / 'dispose-not-invoked.json').exists()
    proof, ref, rev = complete_and_revalidate(ce, call, c, cfg)
    assert proof['alarm']['dispose_invoked'] is True
    assert proof['alarm']['classification'] == 'valid_nonarmed'
    record('nonarmed_actual_cleanup_once_certify_seal_revalidate',
           {'body': {k: body[k] for k in ('alarm_disposition', 'errors')},
            'dispose_invoked': proof['alarm']['dispose_invoked'],
            'revalidated': True, 'actual_cleanup_once': True})

    # 3. Browser still live after close: actual _cleanup_once body then certify refuses.
    call, c, alarm, state = make_call(cleanup, ce, 'armed', after_active=True)
    body = cleanup._cleanup_once(c, call)
    try:
        ce.certify(call, c, cfg, body, probe)
        raise AssertionError('browser live accepted')
    except Exception as exc:
        assert 'browser_close_unproven' in repr(exc), repr(exc)
    record('browser_still_live_refused', {'refusal': 'browser_close_unproven'})

    # 4. Nonarmed missing original dispose: actual _cleanup_once records error; certify refuses.
    call, c, alarm, state = make_call(cleanup, ce, 'nonarmed', dispose_ok=False)
    body = cleanup._cleanup_once(c, call)
    assert body['errors'], body
    try:
        ce.certify(call, c, cfg, body, probe)
        raise AssertionError('missing dispose accepted')
    except Exception as exc:
        assert 'cleanup_body_incomplete' in repr(exc), repr(exc)
    record('nonarmed_missing_dispose_refused', {'body_errors': body['errors']})

    # 5. Armed missing dispose-not-invoked after actual writer: certify refuses.
    call, c, alarm, state = make_call(cleanup, ce, 'armed')
    body = cleanup._cleanup_once(c, call)
    (call / 'dispose-not-invoked.json').unlink()
    try:
        ce.certify(call, c, cfg, body, probe)
        raise AssertionError('missing armed marker accepted')
    except Exception as exc:
        assert 'armed_dispose_not_invoked_missing' in repr(exc), repr(exc)
    record('armed_missing_dispose_not_invoked_refused', {'refusal': 'armed_dispose_not_invoked_missing'})

    # 6. Armed wrong nonce in marker: certify refuses.
    call, c, alarm, state = make_call(cleanup, ce, 'armed')
    body = cleanup._cleanup_once(c, call)
    ni = json.loads((call / 'dispose-not-invoked.json').read_text())
    ni['nonce'] = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
    wj(call / 'dispose-not-invoked.json', ni)
    try:
        ce.certify(call, c, cfg, body, probe)
        raise AssertionError('wrong nonce accepted')
    except Exception as exc:
        assert 'armed_dispose_field_identity' in repr(exc), repr(exc)
    record('armed_wrong_nonce_refused', {'refusal': 'armed_dispose_field_identity'})

    # 7. Unknown alarm: actual _cleanup_once writes negative marker; certify refuses.
    bad = {'version': 1, 'deadline_ms': 20000, 'expectedURL': URL, 'expectedLaunchId': LAUNCH,
           'documentTimeOrigin': ORIGIN, 'sealed': False,
           'current': {'nonce': NONCE, 'state': 'armed', 'armed_ms': 1000.0, 'due_ms': 21000.0,
                       'deadline_ms': 20000}, 'events': []}
    call, c, alarm, state = make_call(cleanup, ce, 'armed', alarm=bad)
    body = cleanup._cleanup_once(c, call)
    assert body['alarm_disposition'] == 'unknown_malformed', body
    try:
        ce.certify(call, c, cfg, body, probe)
        raise AssertionError('unknown malformed alarm accepted')
    except Exception as exc:
        assert 'alarm_identity_malformed' in repr(exc), repr(exc)
    record('unknown_alarm_refused', {'body_disposition': body['alarm_disposition']})

    passed = sum(1 for r in RESULTS if r['passed'])
    receipt = {'schema': 'fx3-r47-cleanup-closed-loop-test-v1', 'offline': True, 'browser': False,
               'server': False, 'network': False, 'VM': False, 'QMP': False, 'guest': False,
               'actual_cleanup_once_called': True, 'real_browser_used': False, 'pid_probe_used': False,
               'resource_probe': 'injected fake', 'native_evidence': 'injected fake',
               'cleanup_sha256': sha(HERE / 'runtime-wrapper/cleanup.py'),
               'cleanup_evidence_sha256': sha(HERE / 'runtime-wrapper/cleanup_evidence.py'),
               'cases_total': len(RESULTS), 'cases_passed': passed,
               'cases_failed': len(RESULTS) - passed, 'results': RESULTS}
    (RECEIPTS / 'cleanup-closed-loop-tests.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'cases_total': len(RESULTS), 'cases_passed': passed,
                      'receipt': str(RECEIPTS / 'cleanup-closed-loop-tests.json')}))
    return 0 if passed == len(RESULTS) else 1


if __name__ == '__main__':
    sys.exit(main())
