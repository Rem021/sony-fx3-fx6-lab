#!/usr/bin/env python3
"""Read-only r48 HAR/click reconstruction; no browser/VM/process contact."""
import datetime
import hashlib
import json
from pathlib import Path

DEL = Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery')
RUN = DEL / 'r47-runtime-integration-candidate/run-inputs/f9c618eedbad'
CALL = RUN / 'cleanup-calls/dc3a1077-4b0d-4bff-8351-ff77d26c582b'
OUT = DEL / 'r49-frame-admission-analysis/receipts'
OUT.mkdir(parents=True, exist_ok=True)
CLICKED_SHA = 'e0140ea1b701cf45e51290ee48835946edc28078954970230a56617964d56ec4'
PREFLIGHT_SHA = '2914275caea536ff83d3bd1f884dfb1934e456fb782b5569240547e6add0182e'


def dt(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))


def epoch_ms(s):
    return dt(s).timestamp() * 1000.0


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    har = json.loads((CALL / 'traffic.har').read_text())
    entries = har['log']['entries']
    status = []
    posts = []
    for e in entries:
        r = e['request']
        resp = e['response']
        text = (resp.get('content') or {}).get('text', '') or ''
        if r['method'] == 'POST':
            posts.append({'utc': e['startedDateTime'], 'url': r['url'], 'status': resp['status'],
                          'body_bytes': len(text.encode())})
        if r['method'] == 'GET' and r['url'].endswith('/api/status'):
            try:
                body = json.loads(text)
            except Exception:
                continue
            f = body.get('frame') or {}
            status.append({'index': len(status), 'utc': e['startedDateTime'],
                           'epoch_ms': epoch_ms(e['startedDateTime']),
                           'frame': {'PNG_sha256': f.get('PNG_sha256'),
                                     'content_generation': f.get('content_generation'),
                                     'sequence': f.get('sequence')},
                           'steps': body.get('steps'), 'phase': body.get('phase'),
                           'ready': body.get('ready'), 'busy': body.get('busy'),
                           'review_required': body.get('review_required'),
                           'error': body.get('error'), 'render_valid': body.get('render_valid'),
                           'launch_request_id': body.get('launch_request_id'),
                           'run_incarnation': body.get('run_incarnation')})
    by_attempt = []
    for name in ('step-01-attempt-01', 'step-01-attempt-02'):
        d = json.loads((RUN / name / 'click-receipt.json').read_text())
        o = json.loads((RUN / name / 'outcome.json').read_text())
        ident = json.loads((RUN / name / 'identity.json').read_text())
        snap = d['result']['snapshot']
        origin = float(d['document_time_origin'])
        clicked = snap['click_time_frame']
        loaded = snap['loaded']
        click_perf = float(snap['alarm']['now_ms'])
        click_epoch = origin + click_perf
        # HAR status frame nearest before/at click snapshot, and nearest after.
        before = [s for s in status if s['epoch_ms'] <= click_epoch + 0.001]
        after = [s for s in status if s['epoch_ms'] >= click_epoch - 0.001]
        last_tick = max(before, key=lambda s: s['epoch_ms']) if before else None
        pre = min(after, key=lambda s: s['epoch_ms']) if after else None
        # If the nearest after is the same as last tick, take the next one.
        if pre is last_tick:
            idx = status.index(pre)
            pre = status[idx + 1] if idx + 1 < len(status) else None
        # The PAGE preflight is the first status request after click; the nearest
        # after click should be it in this run. Keep both if timing is ambiguous.
        pre_frame = pre['frame'] if pre else None
        frame_loaded_preflight = bool(pre_frame and loaded['generation'] == pre_frame['content_generation'] and
                                      loaded['sha256'] == pre_frame['PNG_sha256'])
        frame_loaded_last = bool(last_tick and loaded['generation'] == last_tick['frame']['content_generation'] and
                                 loaded['sha256'] == last_tick['frame']['PNG_sha256'])
        page = snap['page']
        identity_ok = all(page.values()) and snap.get('identity_trusted') is True
        lifecycle_ok = not any([snap.get('ending'), snap.get('finished'), snap.get('delivery_unknown'),
                                snap.get('review_unknown'), snap.get('review_awaiting'),
                                snap.get('render_fault_present'), snap.get('page_busy'),
                                snap.get('server_busy'), snap.get('review_required'),
                                snap.get('error_present'), snap.get('ready') is not True,
                                snap.get('phase') != 'ready', snap.get('awaiting_step') is not None])
        frame_terms = {
            'preflight_frame_sha_equals_clicked': pre_frame is not None and pre_frame['PNG_sha256'] == clicked['PNG_sha256'],
            'preflight_generation_equals_clicked': pre_frame is not None and pre_frame['content_generation'] == clicked['content_generation'],
            'preflight_sequence_equals_clicked': pre_frame is not None and pre_frame['sequence'] == clicked['sequence'],
            'frame_loaded_for_preflight': frame_loaded_preflight,
            'frame_loaded_for_lastStatus': frame_loaded_last,
            'shown_sha_equals_clicked': loaded['sha256'] == clicked['PNG_sha256'],
            'displayed_generation_equals_clicked': loaded['generation'] == clicked['content_generation'],
        }
        fail_terms = []
        if not frame_terms['preflight_frame_sha_equals_clicked']:
            fail_terms.append('preflight.frame.PNG_sha256 !== clickedSHA')
        if not frame_terms['preflight_generation_equals_clicked']:
            fail_terms.append('preflight.frame.content_generation !== clickedGeneration')
        if not frame_terms['frame_loaded_for_preflight']:
            fail_terms.append('!frameLoadedFor(preflight)')
        if not frame_terms['shown_sha_equals_clicked']:
            fail_terms.append('shownSHA !== clickedSHA')
        if not frame_terms['displayed_generation_equals_clicked']:
            fail_terms.append('displayedGeneration !== clickedGeneration')
        identity_lifecycle_terms = {
            'steps_equal': (pre['steps'] if pre else None) == (last_tick['steps'] if last_tick else None),
            'phase_ready': (pre or {}).get('phase') == 'ready',
            'ready_true': (pre or {}).get('ready') is True,
            'busy_false': (pre or {}).get('busy') is False,
            'review_required_false': (pre or {}).get('review_required') is False,
            'error_absent': (pre or {}).get('error') is None,
            'render_valid': (pre or {}).get('render_valid') is True,
            'launch_equal_click': (pre or {}).get('launch_request_id') == snap.get('launch'),
            'run_incarnation_equal': (pre or {}).get('run_incarnation') == o.get('document_time_origin') if False else (pre or {}).get('run_incarnation') is not None,
        }
        by_attempt.append({
            'case': name, 'attempt_id': o['attempt_id'], 'nonce': o['alarm_nonce'],
            'target': d.get('target'), 'hook_status': d.get('status'),
            'clicked_frame': clicked, 'loaded': loaded, 'click_status_frame': snap.get('status_frame'),
            'click_snapshot_page_performance_ms': click_perf,
            'click_snapshot_utc_approx': dt(datetime.datetime.fromtimestamp(click_epoch / 1000, datetime.timezone.utc).isoformat()).isoformat(),
            'clock_mapping': 'approximate: HAR startedDateTime wall clock minus document_time_origin treated as page-performance; not same monotonic clock; sub-ms/1ms values not exact same-clock measurements',
            'last_status_before': last_tick, 'preflight_status': pre,
            'preflight_utc': pre['utc'] if pre else None,
            'click_to_preflight_ms_approx': (pre['epoch_ms'] - click_epoch) if pre else None,
            'last_tick_to_click_ms_approx': (click_epoch - last_tick['epoch_ms']) if last_tick else None,
            'last_tick_to_preflight_ms_approx': (pre['epoch_ms'] - last_tick['epoch_ms']) if pre and last_tick else None,
            'timing_status': 'approximate_wall_clock_mapping',
            'frame_change_window': {'last_old_observation_utc': last_tick['utc'] if last_tick else None,
                                    'fresh_preflight_utc': pre['utc'] if pre else None,
                                    'note': 'the frame change is observed only between the last old frame observation and the fresh preflight read; the click snapshot lies inside this interval; do not claim the change occurred within 1 ms after the click or in the same monotonic clock'},
            'sequence_note': 'preflight.sequence changed observably, but PAGE lines 304-305 do not directly compare sequence; sequence is not a branch term',
            'outcome': {k: o[k] for k in ('outcome', 'reason', 'mutation_called', 'created_monotonic_ms', 'updated_monotonic_ms')},
            'identity': {'attempt_id': ident.get('attempt_id'), 'nonce': ident.get('nonce'), 'UTC': ident.get('UTC')},
            'frame_terms': frame_terms, 'failing_frame_terms': fail_terms,
            'sequence_is_direct_gate_term': False,
            'identity_lifecycle_terms': identity_lifecycle_terms,
            'identity_ok_from_click_receipt': identity_ok, 'lifecycle_ok_from_click_snapshot': lifecycle_ok,
            'page': page, 'page_ready': snap.get('ready'), 'page_busy': snap.get('page_busy'),
            'server_busy': snap.get('server_busy'), 'review_required': snap.get('review_required'),
            'after_click_key_post_count': sum(1 for p in posts if '/api/key' in p['url']),
        })
    value = {'schema': 'fx3-r49-har-transitions-v1', 'source_har': str(CALL / 'traffic.har'),
             'har_sha256': sha(CALL / 'traffic.har'), 'entries': len(entries),
             'post_paths': posts, 'api_key_post_count': sum(1 for p in posts if '/api/key' in p['url']),
             'status_count': len(status), 'status_frames': status,
             'attempts': by_attempt,
             'fact': 'HAR shows only /api/start, /api/stop, /api/final-ack POSTs; no /api/key POST in this run.',
             'clock_mapping': {'method': 'HAR startedDateTime and document_time_origin are mapped as approximate wall-clock epoch values; not a same monotonic clock; 1ms precision is not exact', 'frame_change_window': 'between last old frame observation and fresh preflight read; cannot bound to after click'},
             'method': 'HAR status response frames plus click receipts; approximate wall-clock mapping only; no cross-clock CPU/FIFO/HTTP inference'}
    (OUT / 'har-transitions.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'post_paths': [p['url'] for p in posts], 'api_key_post_count': value['api_key_post_count'],
                      'attempts': [{'case': a['case'], 'clicked': a['clicked_frame'], 'preflight': a['preflight_status']['frame'] if a['preflight_status'] else None,
                                    'click_to_preflight_ms_approx': a['click_to_preflight_ms_approx'], 'failing': a['failing_frame_terms'],
                                    'outcome': a['outcome']['outcome']} for a in by_attempt]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
