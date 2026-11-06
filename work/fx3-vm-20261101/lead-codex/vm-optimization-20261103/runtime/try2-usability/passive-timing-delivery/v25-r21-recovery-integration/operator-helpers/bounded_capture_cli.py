#!/usr/bin/env python3
"""Read-only, one-shot first-MENU reference capture in one explicit CLI call.

No guest key, End, confirm, arm, cancel, navigation, or direct HTTP operation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
MENU_SHA = '60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292'
UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
SESSION = re.compile(r'fx3-deadline-[A-Za-z0-9_-]+')


def utc():
    return datetime.now(timezone.utc).isoformat()


def browser(session, args, *, source=None, timeout=15):
    p = subprocess.run(['agent-browser', '--session', session, *args], input=source,
                       text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f'agent-browser {args[0]}: {p.stdout} {p.stderr}')
    return p.stdout


def validate(session, url, launch_id, nonce):
    if not SESSION.fullmatch(session):
        raise ValueError('owned fx3-deadline-* session required')
    parsed = urlsplit(url)
    if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port or
            parsed.path != '/' or parsed.query or parsed.fragment or parsed.username or
            parsed.password or url != f'http://127.0.0.1:{parsed.port}/'):
        raise ValueError('exact loopback URL including trailing slash required')
    if not UUID.fullmatch(launch_id) or not UUID.fullmatch(nonce):
        raise ValueError('launch UUID and current armed nonce required')


def capture(session, url, launch_id, nonce, evidence_dir, *, browser_call=browser):
    validate(session, url, launch_id, nonce)
    out = Path(evidence_dir)
    if not out.parent.is_dir():
        raise ValueError('existing evidence parent required')
    out.mkdir()  # Exclusive: never overwrite an earlier screenshot or receipt.
    receipt = {'status': 'no_qualified_screenshot', 'scope': 'first_MENU_reference_only',
               'reference_png_sha256': MENU_SHA, 'session': session, 'url': url,
               'launch_id': launch_id, 'alarm_nonce': nonce, 'step': 1,
               'host_started_UTC': utc(), 'host_monotonic_started': time.monotonic(),
               'screenshot_attempted': False, 'guest_keys_sent': 0,
               'confirm_calls': 0, 'alarm_mutations': 0, 'timeline': []}
    def stamp(label):
        receipt['timeline'].append({'stage': label, 'UTC': utc(), 'monotonic': time.monotonic()})
    def timed(label, fn):
        stamp(label + '_enter')
        try:
            return fn()
        finally:
            stamp(label + '_exit')
    result_path = out / 'capture-result.json'
    stamp('initial_receipt_write_enter')
    result_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    stamp('initial_receipt_write_exit')
    try:
        tabs = json.loads(timed('tab_preflight', lambda:
            browser_call(session, ['tab', '--json'])))['data']['tabs']
        if len(tabs) != 1 or tabs[0]['url'] != url:
            raise ValueError('exactly one owned tab at the exact URL required')
        receipt['tab_id'] = tabs[0].get('id')
        config = {'url': url, 'launch_id': launch_id, 'nonce': nonce,
                  'step': 1, 'reference_sha': MENU_SHA}
        raw = timed('before_eval', lambda: browser_call(session, ['eval', '--stdin'],
                    source=(HERE / 'bounded_capture.js').read_text() +
                    '(' + json.dumps(config) + ')', timeout=12))
        pre = json.loads(raw)
        receipt['before_eval'] = pre
        if pre.get('status') != 'ready_for_screenshot':
            receipt['reason'] = pre.get('reason', 'pre_screenshot_refused')
            return receipt
        before = pre['before']
        if (before.get('png_sha256') != MENU_SHA or before.get('step') != 1 or
                before.get('review_step') != 1 or before.get('due_ms', 0) -
                before.get('performance_ms', 0) < 8000):
            receipt['reason'] = 'pre_screenshot_identity_or_reserve'
            return receipt
        shot = out / 'menu-reference-page.png'
        receipt['screenshot_attempted'] = True
        # A screenshot is not a semantic judgement. Keep it even if the post-check fails.
        timed('screenshot', lambda: browser_call(session, ['screenshot', str(shot)], timeout=12))
        receipt['screenshot_file_sha256'] = hashlib.sha256(shot.read_bytes()).hexdigest()
        receipt['screenshot_file_bytes'] = shot.stat().st_size
        after_config = {'url': url, 'launch_id': launch_id, 'nonce': nonce,
                        'reference_sha': MENU_SHA, 'due_token': before['due_token'],
                        'document_origin_token': before['document_origin_token'],
                        'sequence': before['sequence'],
                        'content_generation': before['content_generation']}
        after_script = (HERE / 'capture_after.js').read_text().replace(
            'CONFIG', json.dumps(after_config), 1)
        after = json.loads(timed('after_eval', lambda:
            browser_call(session, ['eval', '--stdin'], source=after_script, timeout=5)))
        receipt['after_eval'] = after
        if not after.get('qualified'):
            receipt['reason'] = 'post_screenshot_identity_or_reserve_changed'
            return receipt
        receipt['status'] = 'qualified_screenshot_for_operator_review'
        receipt['reason'] = 'loaded_reference_identity_stable_before_and_after_screenshot'
        receipt['screenshot_path'] = str(shot)
        return receipt
    except BaseException as exc:
        receipt['reason'] = 'capture_error_or_delivery_unknown'
        receipt['error'] = repr(exc)
        return receipt
    finally:
        receipt['host_finished_UTC'] = utc()
        receipt['host_monotonic_finished'] = time.monotonic()
        receipt['host_elapsed_ms'] = round(1000 * (receipt['host_monotonic_finished'] -
                                                 receipt['host_monotonic_started']), 3)
        stamp('final_receipt_write_enter')
        result_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
        stamp('final_receipt_write_exit')
        stamp('return_boundary')
        result_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ('session', 'url', 'launch-id', 'nonce', 'evidence-dir'):
        p.add_argument('--' + arg, required=True)
    a = p.parse_args()
    result = capture(a.session, a.url, a.launch_id, a.nonce, a.evidence_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['status'] == 'qualified_screenshot_for_operator_review' else 2)
