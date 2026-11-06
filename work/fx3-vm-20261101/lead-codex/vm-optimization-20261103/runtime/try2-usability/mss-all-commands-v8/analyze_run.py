#!/usr/bin/env python3
"""Read-only summary of one bounded MSS observer run; sends are not consumes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

parser = argparse.ArgumentParser()
parser.add_argument('run', type=Path)
args = parser.parse_args()
run = args.run.resolve()
serial = (run / 'serial.log').read_bytes()
receipt = json.loads((run / 'receipt.json').read_text())
pattern = re.compile(
    rb'FX3_MSS_ORIGINAL_PATH seq=(\d+) ns=(\d+) tid=(\d+) point=(0x[0-9a-f]+) '
    rb'call_id=(\d+) qid=(0x[0-9a-f]+|0) cmd=(0x[0-9a-f]+|0) phase=(\w+) '
    rb'[^\r\n]*?x0=(0x[0-9a-f]+|0) [^\r\n]*?source=(0x[0-9a-f]+|0) '
    rb'raw16=(unreadable|[0-9a-f]{32}) readable=([01])'
)
records = []
for match in pattern.finditer(serial):
    seq, ns, tid, point, call_id, qid, cmd, phase, x0, source, raw, readable = match.groups()
    records.append({'seq': int(seq), 'guest_ns': int(ns), 'tid': int(tid),
                    'point': point.decode(), 'call_id': int(call_id),
                    'qid': qid.decode(), 'cmd': cmd.decode(), 'phase': phase.decode(),
                    'x0': x0.decode(), 'source': source.decode(),
                    'raw16': raw.decode(), 'raw_ok': bool(int(readable)),
                    'serial_offset': match.start()})
assert all(record['seq'] == i for i, record in enumerate(records, 1))
calls = {}
for record in records:
    if record['phase'] not in ('entry', 'return'):
        continue
    assert record['qid'] == '0x80924220'
    pair = calls.setdefault(record['call_id'], {})
    assert record['phase'] not in pair
    pair[record['phase']] = record
paired = []
for call_id, pair in sorted(calls.items()):
    assert set(pair) == {'entry', 'return'}, (call_id, pair)
    a, b = pair['entry'], pair['return']
    assert a['tid'] == b['tid'] and a['cmd'] == b['cmd'] and a['source'] == b['source']
    assert a['guest_ns'] <= b['guest_ns']
    paired.append({'call_id': call_id, 'cmd': a['cmd'], 'source': a['source'],
                   'tid': a['tid'], 'entry_guest_ns': a['guest_ns'],
                   'return_guest_ns': b['guest_ns'], 'return_x0': b['x0'],
                   'raw_ok': b['raw_ok']})
out = {'schema': 'fx3-mss-all-commands-observer-v1', 'run': str(run),
       'serial_sha256': hashlib.sha256(serial).hexdigest(), 'serial_bytes': len(serial),
       'candidate_sha256': receipt['candidate_sha256'],
       'source_observer': 'injected passive appFw.so ordinary-instruction hook, not original kernel log',
       'original_queue': '0x80924220', 'records': len(records), 'paired_calls': len(paired),
       'command_counts': dict(sorted(Counter(call['cmd'] for call in paired).items())),
       'overflow_lines': len(re.findall(rb'FX3_MSS_ORIGINAL_PATH_OVERFLOW', serial)),
       'raw_ok_calls': sum(call['raw_ok'] for call in paired),
       'calls': paired,
       'key_steps': receipt['key_steps'], 'host_observer_error': receipt['host_observer_error'],
       'stop_cause': receipt['stop_cause'], 'native_power_off': receipt['native_model_power_off_after_ready'],
       'native_shutdown': receipt['native_shutdown_after_ready'],
       'qemu_exit': receipt['qemu_exit'], 'process_reaped': receipt['process_reaped'],
       'pid_absent': receipt['PID_absent'], 'api16_restored': receipt['cleanup']['API16_restored'],
       'inputs_unchanged': receipt['inputs_unchanged'], 'locks': receipt['locks'],
       'interpretation_guard': 'entry and return are original app send-path observations only; no UPM receive, timer start, or raw16 packet claim when raw_ok=0'}
path = Path(__file__).with_name(run.name + '-analysis.json')
path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({key: out[key] for key in ('serial_sha256', 'records', 'paired_calls',
                                            'command_counts', 'overflow_lines', 'raw_ok_calls',
                                            'key_steps', 'stop_cause')}, indent=2))
