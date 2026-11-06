#!/usr/bin/env python3
"""Offline r46 cleanup-evidence tests. No VM/browser/server/QMP/guest/deployment.

The candidate module is imported directly; native evidence and the current-resource
probe are injected fakes so the tests never touch a real browser, process or run.
The r45 armed replay copies only the already-sealed cleanup call into a candidate
temporary directory and adds the artifacts the *candidate* would have written; the
original r45 call is read-only and remains unknown.
"""
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
DEL = HERE.parent
EVID = DEL / 'r44-review-budget-candidate/run-inputs/r45-vm-r45vm0323'
R45_CALL = EVID / 'cleanup-calls/4302ff41-653d-4ae5-9b79-f713120ab9e2'
SPECDIR = HERE / 'runtime-wrapper'
spec = importlib.util.spec_from_file_location('r46_cleanup_evidence', SPECDIR / 'cleanup_evidence.py')
ce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ce)

URL = 'http://127.0.0.1:58245/'
LAUNCH = 'd23ffef6-215c-41a8-80b6-0da39ac31114'
NONCE = 'd1b0d0c4-0eff-4ca9-9c61-46c15384101c'
DOC = '70f5e6af-bcaf-4fdf-8177-520fff7a31a7'
ORIGIN = 1793877848674.9
RUN = '9cab2340-e878-4c3a-8229-e10e989798fa'
SESSION = 'fx3-deadline-r46test'
RUNNER_PID = 53378
QEMU_PID = 53782
NATIVE = {'files': {'command.json': {'path': '/sealed/command.json', 'sha256': 'a' * 64, 'bytes': 1}},
          'qemu_pid': QEMU_PID, 'host_launch_uuid': 'b1f17b5a-4e34-4cb9-ba4b-d43838c36de9',
          'locks': ['/lock/a', '/lock/b'], 'scope': 'test-captured-native'}
BINDING = {'candidate_run_dir': '/sealed/run', 'session': SESSION, 'task_id': 't', 'dispatch_id': 'd',
           'source_root': '/sealed/source', 'profile': 'r46-test', 'source_sha256': 'a' * 64,
           'core_sha256': 'b' * 64, 'config_sha256': 'c' * 64, 'runtime_sha256': 'd' * 64,
           'local_freeze_sha256': 'e' * 64, 'runtime': {'url': URL, 'run': '/sealed/native', 'runner_pid': RUNNER_PID,
                                                        'launch_id': LAUNCH}}
CFG = {'session': SESSION}
RESULTS = []
TMP = Path(tempfile.mkdtemp(prefix='r46-cleanup-', dir=(HERE / 'receipts/raw'))).resolve()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def wj(p, v):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n')


def process(call, name, stdout=None, returncode=0):
    rec = {'argv': [], 'start': {'UTC': 'x', 'host_ns': 1}, 'end': {'UTC': 'x', 'host_ns': 2},
           'returncode': returncode, 'stdout': json.dumps(stdout) if stdout is not None else '', 'stderr': ''}
    wj(Path(call) / (name + '-process.json'), rec)


def probe(c, q):
    return {'resources_closed': True, 'runner_pid': c['runner_pid'], 'qemu_pid': q,
            'runner_absent': True, 'qemu_absent': True, 'port_closed': True,
            'port_connect_errno': 61, 'locks': [{'path': '/lock/a', 'free_at_probe': True},
                                                {'path': '/lock/b', 'free_at_probe': True}], 'errors': []}


def check(name, fn):
    try:
        detail = fn()
        RESULTS.append({'case': name, 'passed': True, 'detail': detail})
        print('PASS', name)
    except Exception as exc:  # noqa: BLE001
        RESULTS.append({'case': name, 'passed': False, 'error': repr(exc)})
        print('FAIL', name, repr(exc))
        raise


def expect_refused(fn, *needles):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        text = repr(exc)
        assert any(n in text for n in needles), (needles, text)
        return text
    raise AssertionError('expected refusal, got success')


def armed_alarm(current_nonce=NONCE, due=61000.0, state='armed'):
    cur = {'nonce': current_nonce, 'state': state, 'armed_ms': 1000.0, 'due_ms': due, 'deadline_ms': 60000}
    events = [{'event': 'installed', 'performance_ms': 10.0, 'script_SHA256': 'f' * 64},
              {'event': 'armed', 'nonce': current_nonce, 'due_ms': due, 'performance_ms': 1000.0}]
    return {'version': 1, 'deadline_ms': 60000, 'expectedURL': URL, 'expectedLaunchId': LAUNCH,
            'documentTimeOrigin': ORIGIN, 'sealed': False, 'current': cur, 'events': events}


def make_armed(disposition='valid_armed_do_not_cancel_or_dispose', alarm=None, document_id=DOC,
               origin=ORIGIN, launch=LAUNCH, finished=True, ending=True, end_invoked=True,
               browser_before=True, browser_after=False, stage_rc=0, body_over=None,
               write_not_invoked=True, write_dispose=False, marker_over=None, not_invoked_over=None,
               current_attempt=True):
    root = Path(tempfile.mkdtemp(prefix='call-', dir=TMP)).resolve()
    here = root / 'HERE'
    call = here / 'cleanup-calls' / '11111111-1111-4111-8111-111111111111'
    call.mkdir(parents=True)
    al = alarm or armed_alarm()
    wj(call / 'deadline-after-End.json', al)
    state = {'finished': finished, 'ending': ending, 'url': URL, 'document_id': document_id,
             'document_time_origin': origin, 'alarm': al,
             'lastStatus': {'phase': 'finished' if finished else 'ready',
                            'launch_request_id': launch, 'run_incarnation': RUN}}
    wj(call / 'ENDED-STATE.json', state)
    body = {'errors': [], 'alarm_disposition': disposition, 'runner_pid': RUNNER_PID,
            'runner_alive': False, 'port_closed': True, 'bounded_final_recheck_seconds': 5}
    body.update(body_over or {})
    wj(call / 'body-result.json', body)
    if write_not_invoked:
        ni = {'reason': disposition, 'alarm_cleanup': 'no cancel/no dispose; owned document closes below',
              'alarm_sha256': sha(call / 'deadline-after-End.json'), 'alarm': al,
              'version': al['version'], 'deadline_ms': al['deadline_ms'], 'expectedURL': al['expectedURL'],
              'expectedLaunchId': al['expectedLaunchId'], 'documentTimeOrigin': al['documentTimeOrigin'],
              'sealed': al['sealed'], 'nonce': al['current']['nonce'], 'state': al['current']['state'],
              'armed_ms': al['current']['armed_ms'], 'due_ms': al['current']['due_ms'],
              'current_deadline_ms': al['current']['deadline_ms']}
        ni.update(not_invoked_over or {})
        wj(call / 'dispose-not-invoked.json', ni)
    if write_dispose:
        dcur = dict(al['current'])
        dispose = {'version': 1, 'deadline_ms': 60000, 'expectedURL': URL, 'expectedLaunchId': LAUNCH,
                   'documentTimeOrigin': ORIGIN, 'sealed': True, 'current': dcur,
                   'events': [{'event': 'disposed', 'performance_ms': 2000.0}]}
        wj(call / 'deadline-dispose.json', dispose)
        process(call, 'deadline-dispose', {})
    marker = {'classification': disposition, 'forced_cancel': False,
              'dispose_invoked': disposition in ('valid_null_never_armed', 'valid_nonarmed'),
              'alarm_sha256': sha(call / 'deadline-after-End.json')}
    marker.update(marker_over or {})
    wj(call / 'ALARM-DISPOSITION.json', marker)
    process(call, 'End-original-button', {'End_invoked': end_invoked, 'finished': finished, 'ending': ending})
    process(call, 'ended-state', {})
    process(call, 'ended-page', {}, stage_rc)
    process(call, 'deadline-after-End', {})
    process(call, 'HAR-stop', {}, stage_rc)
    process(call, 'browser-before-close', {'success': True, 'data': {'session': SESSION,
                                                                     'active': browser_before, 'pid': 5555 if browser_before else None}})
    process(call, 'browser-close', {'success': True})
    process(call, 'browser-after-close', {'success': True, 'data': {'session': SESSION,
                                                                    'active': browser_after, 'pid': None if not browser_after else 5555}})
    (call / 'ended-page.png').write_bytes(b'\x89PNG\r\n\x1a\n' + b'x' * 16)
    wj(call / 'traffic.har', {'log': {'entries': []}})
    for n in ('command.json', 'trial-session.json', 'receipt.json', 'trial-web-final-receipt.json',
              'resource-guard-receipt.json'):
        wj(call / 'native' / n, {})
    if current_attempt:
        wj(here / 'current-attempt.json', {'step': 8, 'nonce': NONCE, 'attempt_id': 'att',
                                          'postkey_binding': {'document_id': DOC, 'document_time_origin': ORIGIN,
                                                              'run_incarnation': RUN}})
    c = {'url': URL, 'run': '/sealed/native', 'runner_pid': RUNNER_PID, 'launch_id': LAUNCH}
    return call, c, body


def completed_receipt(call, c, cfg):
    proof = ce.certify(call, c, cfg, json.loads((call / 'body-result.json').read_text()), probe)
    wj(call / 'proof.json', proof)
    wj(call / 'invocation.json', {'schema': ce.SCHEMA, 'call_id': call.name, 'binding': BINDING, 'owner': True})
    value = {'schema': ce.SCHEMA, 'call_id': call.name, 'status': 'completed', 'errors': [],
             'binding': BINDING, 'resources': proof['resources'], 'original_action_outcome': 'unchanged'}
    wj(call / 'result.json', value)
    (call / 'stdout.txt').write_text('{}\n')
    (call / 'stderr.txt').write_text('')
    public = json.dumps(value, ensure_ascii=False) + '\n'
    (call / 'return.stdout.txt').write_text(public)
    wj(call / 'RETURN-HASH.json', {'sha256': hashlib.sha256(public.encode()).hexdigest(),
                                   'bytes': len(public.encode()), 'scope': 'exact public stdout'})
    ref = ce.seal(call)
    return ref, value, proof


def make_nonarmed(cancelled=True):
    if cancelled:
        current = {'nonce': NONCE, 'state': 'cancelled', 'armed_ms': 1000.0, 'due_ms': 61000.0,
                   'cancelled_ms': 3000.0, 'deadline_ms': 60000}
        events = [{'event': 'installed'}, {'event': 'armed', 'nonce': NONCE, 'due_ms': 61000.0},
                  {'event': 'cancelled', 'nonce': NONCE, 'elapsed_ms': 2000.0}]
    else:
        current = None
        events = [{'event': 'installed'}]
    alarm = {'version': 1, 'deadline_ms': 60000, 'expectedURL': URL, 'expectedLaunchId': LAUNCH,
             'documentTimeOrigin': ORIGIN, 'sealed': False, 'current': current, 'events': events}
    disposition = 'valid_nonarmed' if cancelled else 'valid_null_never_armed'
    call, c, body = make_armed(disposition=disposition, alarm=alarm, write_not_invoked=False,
                               write_dispose=False)
    dispose = {'version': 1, 'deadline_ms': 60000, 'expectedURL': URL, 'expectedLaunchId': LAUNCH,
               'documentTimeOrigin': ORIGIN, 'sealed': True,
               'current': dict(current) if current else None,
               'events': events + [{'event': 'disposed', 'performance_ms': 4000.0}]}
    wj(call / 'deadline-dispose.json', dispose)
    process(call, 'deadline-dispose', {})
    wj(call / 'ALARM-DISPOSITION.json', {'classification': disposition, 'forced_cancel': False,
                                         'dispose_invoked': True,
                                         'alarm_sha256': sha(call / 'deadline-after-End.json')})
    return call, c, body


def run():
    ce.native_evidence = lambda c, folder=None: NATIVE

    def armed_positive():
        call, c, body = make_armed()
        p = ce.certify(call, c, CFG, body, probe)
        assert p['alarm']['classification'] == 'valid_armed_do_not_cancel_or_dispose'
        assert p['alarm']['dispose_invoked'] is False
        assert p['alarm']['nonce'] == NONCE and p['alarm']['due_ms'] == 61000.0
        assert p['ended_state']['End_invoked'] is True and p['ended_state']['current_attempt_bound'] is True
        assert p['browser'] == {'session': SESSION, 'before_pid': 5555, 'after_active': False, 'after_pid': None}
        return {'classification': p['alarm']['classification'], 'dispose_invoked': p['alarm']['dispose_invoked'],
                'nonce': p['alarm']['nonce'], 'due_ms': p['alarm']['due_ms'],
                'End_invoked': p['ended_state']['End_invoked'], 'browser': p['browser'],
                'resources_closed': p['resources']['resources_closed']}
    check('armed_original_End_browser_closed_certifies', armed_positive)

    def armed_missing_dispose_not_invoked():
        call, c, body = make_armed(write_not_invoked=False)
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'armed_dispose_not_invoked_missing')
    check('armed_missing_dispose_not_invoked_refused', armed_missing_dispose_not_invoked)

    def armed_dispose_invoked_refused():
        call, c, body = make_armed(write_dispose=True)
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'armed_dispose_invoked')
    check('armed_with_dispose_artifact_refused', armed_dispose_invoked_refused)

    def armed_wrong_nonce():
        call, c, body = make_armed(not_invoked_over={'nonce': 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'})
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'armed_dispose_field_identity')
    check('armed_wrong_nonce_refused', armed_wrong_nonce)

    def armed_wrong_due():
        call, c, body = make_armed(not_invoked_over={'due_ms': 62000.0})
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'armed_dispose_field_identity')
    check('armed_wrong_due_refused', armed_wrong_due)

    def armed_wrong_document():
        call, c, body = make_armed(document_id='22222222-2222-4222-8222-222222222222')
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'current_attempt_document_or_run')
    check('armed_wrong_document_identity_refused', armed_wrong_document)

    def armed_wrong_origin():
        call, c, body = make_armed(origin=ORIGIN + 1)
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe),
                              'ended_alarm_document_mismatch')
    check('armed_wrong_time_origin_refused', armed_wrong_origin)

    def armed_wrong_launch():
        call, c, body = make_armed(launch='33333333-3333-4333-8333-333333333333')
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'ended_launch_or_run')
    check('armed_wrong_launch_refused', armed_wrong_launch)

    def armed_not_finished():
        call, c, body = make_armed(finished=False)
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'ended_not_finished')
    check('armed_unfinished_End_refused', armed_not_finished)

    def armed_body_errors():
        call, c, body = make_armed(body_over={'errors': ['x']})
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'cleanup_body_incomplete')
    check('armed_body_errors_refused', armed_body_errors)

    def armed_runner_alive():
        call, c, body = make_armed(body_over={'runner_alive': True})
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'cleanup_body_incomplete')
    check('armed_runner_alive_refused', armed_runner_alive)

    def armed_browser_live():
        call, c, body = make_armed(browser_after=True)
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'browser_close_unproven')
    check('armed_browser_still_live_refused', armed_browser_live)

    def armed_browser_before_inactive():
        call, c, body = make_armed(browser_before=False)
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'browser_before_close_not_active')
    check('armed_browser_before_not_active_refused', armed_browser_before_inactive)

    def armed_wrong_marker_digest():
        call, c, body = make_armed(marker_over={'alarm_sha256': '0' * 64})
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'alarm_marker_digest')
    check('armed_marker_digest_refused', armed_wrong_marker_digest)

    def armed_forced_cancel_marker():
        call, c, body = make_armed(marker_over={'forced_cancel': True})
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'alarm_marker_classification')
    check('armed_forced_cancel_marker_refused', armed_forced_cancel_marker)

    def armed_body_disposition_mismatch():
        call, c, body = make_armed()
        body['alarm_disposition'] = 'valid_nonarmed'
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'alarm_disposition_mismatch')
    check('body_disposition_mismatch_refused', armed_body_disposition_mismatch)

    def armed_stage_failure():
        call, c, body = make_armed(stage_rc=1)
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'incomplete_stage')
    check('stage_failure_refused', armed_stage_failure)

    def armed_resources_live():
        call, c, body = make_armed()
        bad = lambda c, q: {'resources_closed': False, 'errors': ['port: open']}
        return expect_refused(lambda: ce.certify(call, c, CFG, body, bad), 'current_resources_unproven')
    check('armed_live_resource_probe_refused', armed_resources_live)

    def armed_bad_png():
        call, c, body = make_armed()
        (call / 'ended-page.png').write_bytes(b'not-a-png')
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'cleanup_PNG_missing')
    check('armed_bad_png_refused', armed_bad_png)

    def armed_bad_har():
        call, c, body = make_armed()
        wj(call / 'traffic.har', {'log': {'entries': 'no'}})
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'cleanup_HAR_missing')
    check('armed_bad_har_refused', armed_bad_har)

    def nonarmed_positive():
        call, c, body = make_nonarmed(cancelled=True)
        p = ce.certify(call, c, CFG, body, probe)
        assert p['alarm']['dispose_invoked'] is True and p['alarm']['classification'] == 'valid_nonarmed'
        return {'classification': p['alarm']['classification'], 'dispose_invoked': p['alarm']['dispose_invoked'],
                'dispose_sha256': p['alarm']['dispose_sha256']}
    check('nonarmed_with_original_dispose_certifies', nonarmed_positive)

    def null_positive():
        call, c, body = make_nonarmed(cancelled=False)
        p = ce.certify(call, c, CFG, body, probe)
        assert p['alarm']['classification'] == 'valid_null_never_armed'
        return {'classification': p['alarm']['classification']}
    check('never_armed_with_dispose_certifies', null_positive)

    def nonarmed_missing_dispose():
        call, c, body = make_nonarmed(cancelled=True)
        (call / 'deadline-dispose.json').unlink()
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'nonarmed_dispose_missing')
    check('nonarmed_missing_dispose_refused', nonarmed_missing_dispose)

    def nonarmed_dispose_not_sealed():
        call, c, body = make_nonarmed(cancelled=True)
        d = json.loads((call / 'deadline-dispose.json').read_text())
        d['sealed'] = False
        wj(call / 'deadline-dispose.json', d)
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'nonarmed_dispose_unproven')
    check('nonarmed_unsealed_dispose_refused', nonarmed_dispose_not_sealed)

    def nonarmed_dispose_wrong_state():
        call, c, body = make_nonarmed(cancelled=True)
        d = json.loads((call / 'deadline-dispose.json').read_text())
        d['current']['nonce'] = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
        wj(call / 'deadline-dispose.json', d)
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'nonarmed_dispose_unproven')
    check('nonarmed_dispose_wrong_nonce_refused', nonarmed_dispose_wrong_state)

    def nonarmed_extra_armed_artifact():
        call, c, body = make_nonarmed(cancelled=True)
        wj(call / 'dispose-not-invoked.json', {'reason': 'valid_armed_do_not_cancel_or_dispose'})
        return expect_refused(lambda: ce.certify(call, c, CFG, body, probe), 'nonarmed_dispose_not_invoked_artifact')
    check('nonarmed_with_armed_artifact_refused', nonarmed_extra_armed_artifact)

    def classify_malformed():
        assert ce.classify_alarm({'version': 1}, {'url': URL, 'launch_id': LAUNCH}) == 'unknown_malformed'
        bad = armed_alarm()
        bad['deadline_ms'] = 20000
        assert ce.classify_alarm(bad, {'url': URL, 'launch_id': LAUNCH}) == 'unknown_malformed'
        bad = armed_alarm()
        bad['current']['due_ms'] = 60000.0
        assert ce.classify_alarm(bad, {'url': URL, 'launch_id': LAUNCH}) == 'unknown_malformed'
        bad = armed_alarm()
        bad['current']['nonce'] = 'not-a-uuid'
        assert ce.classify_alarm(bad, {'url': URL, 'launch_id': LAUNCH}) == 'unknown_malformed'
        null = {'version': 1, 'deadline_ms': 60000, 'expectedURL': URL, 'expectedLaunchId': LAUNCH,
                'documentTimeOrigin': ORIGIN, 'sealed': False, 'current': None,
                'events': [{'event': 'armed'}]}
        assert ce.classify_alarm(null, {'url': URL, 'launch_id': LAUNCH}) == 'unknown_malformed'
        return 'malformed_alarm_refused'
    check('malformed_alarm_classification_refused', classify_malformed)

    def completed_revalidate_positive():
        call, c, body = make_armed()
        ref, value, proof = completed_receipt(call, c, CFG)
        here = call.parent.parent
        call2, value2 = ce.validate_reference(here, ref)
        assert call2 == call and value2['status'] == 'completed'
        r = ce.revalidate(here, ref, BINDING, c, CFG, probe)
        assert r['original_completed_call'] == call.name
        return {'validated_receipt': ref['call_id'], 'revalidated': True,
                'resources_closed': r['resources']['resources_closed']}
    check('completion_index_validate_and_revalidate', completed_revalidate_positive)

    def completed_revalidate_tamper_result():
        call, c, body = make_armed()
        ref, value, proof = completed_receipt(call, c, CFG)
        v = json.loads((call / 'result.json').read_text()); v['status'] = 'unknown'
        wj(call / 'result.json', v)
        return expect_refused(lambda: ce.validate_reference(call.parent.parent, ref), 'receipt_reference_hash')
    check('tampered_result_refused', completed_revalidate_tamper_result)

    def completed_revalidate_tamper_artifact():
        call, c, body = make_armed()
        ref, value, proof = completed_receipt(call, c, CFG)
        (call / 'ended-page.png').write_bytes(b'\x89PNG\r\n\x1a\n' + b'changed')
        return expect_refused(lambda: ce.validate_reference(call.parent.parent, ref), 'artifact_integrity')
    check('tampered_artifact_refused', completed_revalidate_tamper_artifact)

    def completed_revalidate_tamper_proof():
        call, c, body = make_armed()
        ref, value, proof = completed_receipt(call, c, CFG)
        proof['alarm']['due_ms'] = 99999.0
        wj(call / 'proof.json', proof)
        # proof.json changed but MANIFEST still has the old digest -> artifact_integrity first.
        return expect_refused(lambda: ce.validate_reference(call.parent.parent, ref), 'artifact_integrity')
    check('tampered_proof_refused', completed_revalidate_tamper_proof)

    def publish_index_rules():
        call, c, body = make_armed()
        ref, value, proof = completed_receipt(call, c, CFG)
        here = call.parent.parent
        ce.publish(here, ref, value)
        first = json.loads((here / 'CLEANUP-COMPLETED.json').read_text())
        assert first == ref
        expect_refused(lambda: ce.publish(here, ref, value), 'cannot_replace_unarchived_completion_index')
        raw = b'{invalid json\n'
        (here / 'CLEANUP-COMPLETED.json').write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        archive = here / 'invalid-completed-index.bin'
        archive.write_bytes(raw)
        value2 = dict(value, superseded_invalid_completion={
            'path': str(archive), 'sha256': digest, 'reason': 'tampered'})
        ce.publish(here, ref, value2)
        assert json.loads((here / 'CLEANUP-COMPLETED.json').read_text()) == ref
        # A second replacement with a tampered archive must be refused.
        (here / 'CLEANUP-COMPLETED.json').write_bytes(raw)
        archive.write_bytes(b'changed')
        return expect_refused(lambda: ce.publish(here, ref, value2), 'cannot_replace_unarchived_completion_index')
    check('completion_index_idempotent_and_tamper_refused', publish_index_rules)

    def r45_armed_replay():
        here = Path(tempfile.mkdtemp(prefix='r45-', dir=TMP)).resolve() / 'RUN'
        call = here / 'cleanup-calls' / R45_CALL.name
        shutil.copytree(R45_CALL, call)
        shutil.copy2(EVID / 'current-attempt.json', here / 'current-attempt.json')
        alarm = json.loads((call / 'deadline-after-End.json').read_text())
        cur = alarm['current']
        digest = sha(call / 'deadline-after-End.json')
        wj(call / 'dispose-not-invoked.json', {
            'reason': 'valid_armed_do_not_cancel_or_dispose',
            'alarm_cleanup': 'no cancel/no dispose; owned document closes below',
            'alarm_sha256': digest, 'alarm': alarm, 'version': alarm['version'],
            'deadline_ms': alarm['deadline_ms'], 'expectedURL': alarm['expectedURL'],
            'expectedLaunchId': alarm['expectedLaunchId'],
            'documentTimeOrigin': alarm['documentTimeOrigin'], 'sealed': alarm['sealed'],
            'nonce': cur['nonce'], 'state': cur['state'], 'armed_ms': cur['armed_ms'],
            'due_ms': cur['due_ms'], 'current_deadline_ms': cur['deadline_ms']})
        wj(call / 'ALARM-DISPOSITION.json', {'classification': 'valid_armed_do_not_cancel_or_dispose',
                                             'forced_cancel': False, 'dispose_invoked': False,
                                             'alarm_sha256': digest})
        body = json.loads((call / 'body-result.json').read_text())
        c = {'url': URL, 'run': '/sealed/native', 'runner_pid': RUNNER_PID, 'launch_id': LAUNCH}
        p = ce.certify(call, c, {'session': 'fx3-deadline-r45vm0323'}, body, probe)
        assert p['alarm']['nonce'] == cur['nonce'] and p['alarm']['due_ms'] == cur['due_ms']
        assert p['document_id'] == '70f5e6af-bcaf-4fdf-8177-520fff7a31a7'
        assert p['document_time_origin'] == ORIGIN and p['run_incarnation'] == RUN
        assert p['ended_state']['End_invoked'] is True and p['browser']['before_pid'] == 53382
        return {'source_call': R45_CALL.name, 'copy': str(call), 'proof_passed': True,
                'nonce': p['alarm']['nonce'], 'due_ms': p['alarm']['due_ms'],
                'document_id': p['document_id'], 'document_time_origin': p['document_time_origin'],
                'run_incarnation': p['run_incarnation'], 'End_invoked': p['ended_state']['End_invoked'],
                'browser_before_pid': p['browser']['before_pid'],
                'note': 'copy only; the original r45 cleanup remains unknown'}
    def r45_original_armed_refused():
        here = Path(tempfile.mkdtemp(prefix='r45-orig-', dir=TMP)).resolve() / 'RUN'
        call = here / 'cleanup-calls' / R45_CALL.name
        shutil.copytree(R45_CALL, call)
        body = json.loads((call / 'body-result.json').read_text())
        c = {'url': URL, 'run': '/sealed/native', 'runner_pid': RUNNER_PID, 'launch_id': LAUNCH}
        return expect_refused(lambda: ce.certify(call, c, {'session': 'fx3-deadline-r45vm0323'}, body, probe),
                              'alarm_marker_digest')
    check('r45_original_armed_call_remains_refused', r45_original_armed_refused)

    def r45_first_failed_refused():
        first = EVID / 'cleanup-calls/0687a34f-8dcd-4d62-b4a0-b1c0037830b1'
        here = Path(tempfile.mkdtemp(prefix='r45-first-', dir=TMP)).resolve() / 'RUN'
        call = here / 'cleanup-calls' / first.name
        shutil.copytree(first, call)
        body = json.loads((call / 'body-result.json').read_text())
        c = {'url': URL, 'run': '/sealed/native', 'runner_pid': RUNNER_PID, 'launch_id': LAUNCH}
        return expect_refused(lambda: ce.certify(call, c, {'session': 'fx3-deadline-r45vm0323'}, body, probe),
                              'cleanup_body_incomplete', 'alarm_status_missing')
    check('original_first_failed_call_remains_refused', r45_first_failed_refused)

    check('r45_armed_evidence_replay_certifies_future_cleanup', r45_armed_replay)

    passed = sum(1 for r in RESULTS if r['passed'])
    receipt = {'schema': 'fx3-r46-cleanup-evidence-test-v1', 'offline': True, 'browser': False,
               'server': False, 'network': False, 'VM': False, 'QMP': False, 'guest': False,
               'module_sha256': sha(SPECDIR / 'cleanup_evidence.py'),
               'cleanup_sha256': sha(SPECDIR / 'cleanup.py'),
               'cases_total': len(RESULTS), 'cases_passed': passed,
               'cases_failed': len(RESULTS) - passed, 'results': RESULTS}
    out = HERE / 'receipts/cleanup-evidence-tests.json'
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'cases_total': len(RESULTS), 'cases_passed': passed, 'receipt': str(out)}))
    return 0 if passed == len(RESULTS) else 1


if __name__ == '__main__':
    sys.exit(run())
