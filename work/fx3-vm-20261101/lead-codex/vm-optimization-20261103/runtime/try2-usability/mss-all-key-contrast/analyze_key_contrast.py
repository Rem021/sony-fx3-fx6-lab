#!/usr/bin/env python3
"""Read-only, reproducible correlation of the one MSSv3 key contrast run.

Guest monotonic and host monotonic are separate domains; never subtract them.
App send entry/return is not evidence that the kernel consumed a command.
"""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / 'runs/try2mssallinternal-keycontrast-06db37ef'
serial = (RUN / 'serial.log').read_bytes()
lines = serial.splitlines()
receipt = json.loads((RUN / 'receipt.json').read_text())
ring = json.loads((RUN / 'osd-ring-readback.json').read_text())
inputs = [json.loads(line) for line in (RUN / 'trial-input-events.jsonl').read_text().splitlines()]
assert [event['step'] for event in inputs] == [1, 2, 3]

def fields(line):
    return {key.decode(): value.decode() for key, value in
            re.findall(rb'([a-zA-Z0-9_]+)=([^ ]+)', line)}

records = []
native = []
screens = []
for number, line in enumerate(lines, 1):
    if b'FX3_MSS_ORIGINAL_PATH seq=' in line:
        f = fields(line[line.index(b'FX3_MSS_ORIGINAL_PATH'):])
        records.append({
            'serial_line_1based': number, 'seq': int(f['seq']), 'guest_ns': int(f['ns']),
            'tid': int(f['tid']), 'point': f['point'], 'call_id': int(f['call_id']),
            'qid': f['qid'], 'cmd': f['cmd'], 'phase': f['phase'],
            'source': f['source'], 'raw16': f['raw16'], 'raw_ok': f['readable'] == '1',
            'return_x0': f['x0'] if f['phase'] == 'return' else None,
        })
    if b'FX3_SYNTH_KEY step=' in line:
        f = fields(line[line.index(b'FX3_SYNTH_KEY'):])
        native.append({'serial_line_1based': number, 'step': int(f['step']),
                       'key': f['key'], 'status': int(f['status']),
                       'guest_ns': int(f['monotonic_ns']), 'send_result': int(f['result'])})
    if b'FX3_AP89_SCREEN_OPEN_ENTER' in line:
        f = fields(line[line.index(b'FX3_AP89_SCREEN_OPEN_ENTER'):])
        screens.append({'serial_line_1based': number, 'id1': f['id1'],
                        'id2': f['id2'], 'id3': f['id3'],
                        'meaning': 'original screen-open entry only; creation not yet complete'})

assert [r['seq'] for r in records] == list(range(1, len(records) + 1))
assert len(native) == 6
assert all(not r['raw_ok'] for r in records)
calls = {}
for r in records:
    if r['phase'] in ('entry', 'return'):
        pair = calls.setdefault(r['call_id'], {})
        assert r['phase'] not in pair
        pair[r['phase']] = r
paired = []
for call_id, pair in sorted(calls.items()):
    assert set(pair) == {'entry', 'return'}
    a, b = pair['entry'], pair['return']
    assert (a['tid'], a['qid'], a['cmd'], a['source']) == (b['tid'], b['qid'], b['cmd'], b['source'])
    assert a['guest_ns'] <= b['guest_ns'] and a['qid'] == '0x80924220'
    paired.append({'call_id': call_id, 'cmd': a['cmd'], 'source': a['source'],
                   'tid': a['tid'], 'entry_guest_ns': a['guest_ns'],
                   'return_guest_ns': b['guest_ns'], 'return_x0': b['return_x0'],
                   'entry_serial_line_1based': a['serial_line_1based'],
                   'return_serial_line_1based': b['serial_line_1based'],
                   'raw_ok': a['raw_ok'] and b['raw_ok']})

steps = []
for event in inputs:
    step = event['step']
    matches = [r for r in native if r['step'] == step]
    assert len(matches) == 2 and {r['status'] for r in matches} == {0, 1}
    down, up = next(r for r in matches if r['status'] == 1), next(r for r in matches if r['status'] == 0)
    assert down['guest_ns'] <= up['guest_ns']
    assert all(re.search(rb'FX3_KEY_INPUT_RECV step=%d key=%s status=%d [^\r\n]*native_result=0' %
                         (step, hex(event['key']).encode(), status), serial)
               for status in (0, 1))
    next_down = next((r['guest_ns'] for r in native if r['step'] == step + 1 and r['status'] == 1), None)
    post = [call for call in paired if call['entry_guest_ns'] > up['guest_ns']
            and (next_down is None or call['entry_guest_ns'] < next_down)]
    send_host = event['sent_monotonic']
    next_send_host = next((x['sent_monotonic'] for x in inputs if x['step'] == step + 1), float('inf'))
    prior_poll = max((p for p in ring['polls'] if p['host_monotonic'] <= send_host),
                     key=lambda p: p['host_monotonic'])
    polls = [p for p in ring['polls'] if send_host < p['host_monotonic'] < next_send_host]
    head_advance = next((p for p in polls if p['global_words'][4] != prior_poll['global_words'][4]), None)
    changed = next((f for f in ring['frames'] if send_host < f['host_monotonic'] < next_send_host
                    and f['PNG_sha256'] != event['before_command_png_sha256']), None)
    gaps = [b['host_monotonic'] - a['host_monotonic'] for a, b in zip(polls, polls[1:])]
    capture = json.loads((RUN / f'trial-step-{step:02d}-key-{event["key"]:03x}.json').read_text())
    steps.append({'step': step, 'key': hex(event['key']),
                  'host_requested_monotonic': event['requested_monotonic'],
                  'host_sent_monotonic': event['sent_monotonic'],
                  'guest_down_ns': down['guest_ns'], 'guest_up_ns': up['guest_ns'],
                  'down_serial_line_1based': down['serial_line_1based'],
                  'up_serial_line_1based': up['serial_line_1based'],
                  'post_key_send_call_ids_before_next_key': [c['call_id'] for c in post],
                  'post_key_send_commands': [c['cmd'] for c in post],
                  'host_poll_count_until_next_key_or_exit': len(polls),
                  'host_max_poll_gap_s': max(gaps, default=None),
                  'first_head_advance_after_send_s':
                      head_advance['host_monotonic'] - send_host if head_advance else None,
                  'first_changed_frame_after_send_s':
                      changed['host_monotonic'] - send_host if changed else None,
                  'first_changed_sequence': changed['sequence'] if changed else None,
                  'first_changed_png_sha256': changed['PNG_sha256'] if changed else None,
                  'sampled_frame_sequence': capture['sequence'],
                  'sampled_png_sha256': capture['PNG_sha256'],
                  'sampled_frame_host_monotonic': capture['host_monotonic']})

view_names = [
    'view-step-01-seq-77-2914275caea5.json',
    'view-step-02-seq-434-60e9acccbc46.json',
    'view-step-03-seq-605-15cb5b958cf6.json',
    'trial-step-03-key-030.json',
    'trial-final.json',
]
frames = []
for name in view_names:
    f = json.loads((RUN / name).read_text())
    frames.append({'artifact': name, 'sequence': f['sequence'], 'update_id': f['update_id'],
                   'pixel_source_sequence': f['pixel_source_sequence'],
                   'token': f['token'], 'physical': f['physical'],
                   'host_monotonic': f['host_monotonic'],
                   'png_sha256': f['PNG_sha256'], 'all_zero_pixels': f['all_zero_pixels']})

out = {
    'schema': 'fx3-mssv3-key-contrast-v1', 'run': str(RUN),
    'serial_bytes': len(serial), 'serial_sha256': hashlib.sha256(serial).hexdigest(),
    'candidate_sha256': receipt['candidate_sha256'],
    'observer_source_sha256': next(x['sha256'] for x in receipt['observer_source_snapshot']
                                  if x['name'] == 'run_trial_v17_mss_key_contrast.py'),
    'source_scope': 'injected passive appFw.so ordinary instruction send entry/return, not UPM receive',
    'records': len(records), 'paired_calls': len(paired),
    'sequence_records': [r for r in records if r['phase'] == 'sequence'],
    'overflow_marker_count': serial.count(b'FX3_MSS_ORIGINAL_PATH_OVERFLOW'),
    'raw_ok_count': sum(c['raw_ok'] for c in paired),
    'all_calls': paired, 'steps': steps, 'screens': screens, 'frames': frames,
    'receipt': {'duration_seconds': receipt['duration_seconds'],
                'stop_cause': receipt['stop_cause'], 'key_steps': receipt['key_steps'],
                'qemu_exit': receipt['qemu_exit'], 'process_reaped': receipt['process_reaped'],
                'pid_absent': receipt['PID_absent'], 'api16_restored': receipt['cleanup']['API16_restored'],
                'inputs_unchanged': receipt['inputs_unchanged'], 'locks': receipt['locks'],
                'health_pass': receipt['health_pass']},
}
(HERE / 'key-contrast-analysis.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'serial_sha256': out['serial_sha256'], 'records': len(records),
                  'paired_calls': len(paired), 'overflow_marker_count': out['overflow_marker_count'],
                  'raw_ok_count': out['raw_ok_count'], 'steps': [
                      {'step': x['step'], 'post_key_send_commands': x['post_key_send_commands']}
                      for x in steps]}, indent=2))
