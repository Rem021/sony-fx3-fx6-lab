#!/usr/bin/env python3
"""Offline, existing FX3 evidence only. All writes confined to this directory."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import plistlib
import re
import struct
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if p.name == 'Mac')
TRY = HERE.parents[1]
DEL = HERE.parent
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
INPUTS = {}


def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(p):
    p = p.resolve()
    data = p.read_bytes()
    INPUTS[str(p.relative_to(ROOT))] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    return data


def js(p):
    return json.loads(read(p))


def fields(s):
    return dict(re.findall(r'\b([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)', s))


def num(s):
    return int(s, 16 if s.startswith(('0x', '-0x')) else 10)


def bank(data):
    head = struct.unpack_from('<8Q', data)
    assert head[0] == 0x3145544147335846 and head[1] == 2 and head[2] in (0, 1)
    # v11 struct statistics is 96 u64; header is NOT the counters.
    names = ['peak_all', 'peak_gate', 'field_samples'] + [f'hist{i}' for i in range(6)]
    names += [f'gate_hist{i}' for i in range(6)]
    names += ['system_false', 'backlog_skip', 'time_skip', 'time_pass', 'dequeue_total',
              'timer_dequeue', 'a12_nonzero', 'a13_nonzero', 'last_object', 'last_a18',
              'last_a12', 'last_a13', 'first_ns', 'last_ns', 'mirror_skip', 'selftest', 'bound']
    banks = []
    for i in (0, 1):
        v = struct.unpack_from('<96Q', data, 0x100 + i * 0x1000)
        stats = dict(zip(names, v[64:]))
        stats['counts'] = list(v[:64])
        stats['gate_hist'] = list(v[73:79])
        stats['snapshot_is_transactional'] = False
        stats['clock_id_for_first_last_ns'] = 7
        banks.append(stats)
    return {'header': {'magic': hex(head[0]), 'version': head[1], 'active_bank': head[2],
                       'publication': head[3], 'pid': head[4], 'raw8Q': list(head)},
            'bank_offsets': ['0x100', '0x1100'], 'banks': banks, 'active': banks[head[2]]}


def ring(data):
    h = struct.unpack_from('<6Q', data, 0x2000)
    assert h[0:2] == (0x3147414944353256, 2) and h[3:5] == (256, 96)
    names = ['serial', 'guest_ns', 'tid', 'event_id', 'committed_seq', 'source_seq',
             'id', 'op', 'native_result', 'epoch', 'token', 'link']
    events = dict(enumerate(['produce_enter','produce_return','receive','commit',
                             'wait_enter','wait_return','signal_enter','signal_return'], 1))
    rows, invalid = [], []
    for serial in range(max(1, h[2]-255), h[2]+1):
        offset = 0x2040 + ((serial-1) % 256)*96
        v = struct.unpack_from('<12Q', data, offset)
        if v[0] != serial or v[3] not in events:
            invalid.append({'serial': serial, 'raw': list(v)})
            continue
        r = dict(zip(names, v))
        if r['native_result'] & (1 << 63):
            r['native_result'] -= 1 << 64
        r.update(event=events[v[3]], guest_clock_id=1)
        rows.append(r)
    return {'total': h[2], 'dropped': h[5], 'invalid': invalid, 'rows': rows,
            'counts_in_retained_tail': dict(collections.Counter(r['event'] for r in rows)),
            'last_by_event': {n: next((r for r in reversed(rows) if r['event'] == n), None)
                              for n in events.values()},
            'tail_capacity': 256, 'earlier_events_overwritten': max(0, h[2]-256)}


def run(suffix):
    p = TRY / 'runs' / ('v25diag-web-r6-' + suffix)
    raw = read(p/'serial.log')
    tokens = ['FX3_UI_GATE_SAMPLE ', 'FX3_TIMER_ENTRY ', 'FX3_TIMER_RETURN ',
              'FX3_TIMER_ID ', 'FX3_TIMER_INFO ', 'FX3_TIMER_TABLE ',
              'FX3_UI_FILL_EXEC ', 'FX3_UI_FILL_RETURN ', 'FX3_TIMER_SNAPSHOT ',
              'FX3_KEY_INPUT_RECV ', 'FX3_KEY95_STEP_DONE ', 'FX3_SYNTH_KEY ',
              'FX3_OSD_DRAW_WAIT_RETURN ', 'FX3_OSD_NATIVE_SIGNAL ',
              'FX3_OSD_HEADLESS_ACK ', 'FX3_UI_WIRE ']
    records = {t.strip(): [] for t in tokens}
    offset = 0
    for line_no, line in enumerate(raw.split(b'\n'), 1):
        for token in tokens:
            at = line.find(token.encode())
            if at >= 0:
                s = line[at:].decode(errors='replace').rstrip('\r')
                records[token.strip()].append({'LF_line': line_no, 'byte_offset': offset+at,
                                               'fields': fields(s), 'raw_marker_suffix': s})
        offset += len(line)+1
    gates = {str(i): [r for r in records['FX3_UI_GATE_SAMPLE'] if r['fields'].get('id') == str(i)] for i in range(12)}
    rb = ring(read(p/'osd-ring-final.bin'))
    old = js(p/'osd-ring-final-diag.json')
    assert rb['rows'] == old['rows']
    assert rb['total'] == old['total_accepted_events'] and rb['dropped'] == old['dropped_busy_writer_events']
    assert not rb['invalid'] and not old['invalid_or_torn_slots']
    receipt = js(p/'receipt.json')
    qmp = js(p/'qmp.json')
    qmp_selected = []
    for i, r in enumerate(qmp):
        req = r.get('request', {})
        if 'ui-gate-counters.bin' in str(r) or 'osd-ring-final.bin' in str(r):
            qmp_selected.append({'array_index': i, 'row': r})
    selected_receipt = {k: receipt[k] for k in ['duration_seconds','key_steps','candidate_sha256',
                           'stop_cause','health_pass','protocol_pass','render_pass','lifecycle_pass',
                           'diagnostic_readback_pass','host_observer_error','inputs_unchanged',
                           'native_shutdown_after_ready','native_model_power_off_after_ready',
                           'menu_verified','browser_visual_acceptance','visual_outcomes']}
    selected_receipt['cleanup_snapshot'] = receipt['cleanup']['diag_snapshot']
    selected_receipt['optional_snapshots'] = receipt['cleanup'].get('optional_snapshots')
    summary = {}
    for t, recs in records.items():
        summary[t] = {'count_by_LF': len(recs), 'first': recs[:1], 'last': recs[-1:]}
    output = {'run': str(p.relative_to(ROOT)), 'literal_minus_1018': raw.count(b'-1018'),
              'serial_lines_LF': raw.count(b'\n')+1, 'receipt': selected_receipt,
              'ui_gate': bank(read(p/'ui-gate-counters.bin')), 'ring': rb,
              'ring_binary_matches_existing_json': True, 'marker_summary': summary,
              'gate_samples': gates, 'native_input_receives': records['FX3_KEY_INPUT_RECV'],
              'native_step_done': records['FX3_KEY95_STEP_DONE'],
              'qmp_snapshot_requests': qmp_selected,
              'input_events': [json.loads(s) for s in read(p/'trial-input-events.jsonl').splitlines()],
              'binding_receipt': {'observer_source_snapshot': receipt['observer_source_snapshot'],
                                  'input_checks': receipt['input_checks']}}
    if suffix == '49f9bf9d':
        # Small unsampled interval plus final ordinary samples, rather than whole logs.
        output['wire_tail'] = records['FX3_UI_WIRE'][-12:]
        output['timer_tail'] = records['FX3_TIMER_ENTRY'][-4:] + records['FX3_TIMER_RETURN'][-4:]
        for name in ['command.json','R12-PREFLIGHT.json','R12-web-http-evidence.json',
                     'R12-01-state.json','R12-02-state.json','R12-stop-state.json',
                     'trial-frame.json','trial-final.json','trial-step-readbacks.json',
                     'osd-ring-final-readback-receipt.json','osd-ring-readback.json']:
            output[name] = js(p/name)
        for name in ['R12-01-MENU.png','R12-02-UP.png','R12-02-UP-observe.png',
                     'trial-frame.raw','trial-final.raw','trial-frame.png','trial-final.png',
                     'trial-step-02-key-003.raw','trial-step-02-key-003.png']:
            read(p/name)
        # Native panel copy remained byte-for-byte equal; images were visually inspected.
        assert (p/'trial-final.raw').read_bytes() == (p/'trial-step-02-key-003.raw').read_bytes()
        report = p/'R12-INTERACTION-RESULT.md'
        if report.exists():
            output['runtime_report'] = {'path': str(report.relative_to(ROOT)), 'text': read(report).decode()}
    return output


def main():
    volume = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == UUID
    # Reuse the verified native branches and actual v3/v11/CPIO binding, no new disassembly.
    reused = DEL/'r9-ui-startup-offline'
    for name in ['REPORT.md','EVIDENCE.json','app-main-gate.txt','app-update-and-draw.txt',
                 'app-backlog-producer.txt','app-backlog-consumer.txt','app-timer-1004.txt']:
        read(reused/name)
    helpers = ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/helpers'
    for name in ['fx3-ui-gate-v11.c','fx3-timer-observe-v3.c']:
        read(helpers/name)
    read(DEL/'v25-menu-osd-diagnostic-r3/src/fx3-osd-headless-v25-r3.c')
    runs = {s: run(s) for s in ['49f9bf9d','814c425f','8456422c']}
    for suffix, name in [('814c425f','R11-INTERACTION-RESULT.md'),('8456422c','NAV32-RESULT.md')]:
        read(TRY/'runs'/('v25diag-web-r6-'+suffix)/name)
    # Match stored run-source copies against their receipt entries, never execute them.
    source_comparison = {}
    ref = {v['name']:v['sha256'] for v in runs['49f9bf9d']['binding_receipt']['observer_source_snapshot']}
    for suffix, r in runs.items():
        recorded = {v['name']:v['sha256'] for v in r['binding_receipt']['observer_source_snapshot']}
        for name, sha in recorded.items():
            p = ROOT/r['run']/'observer-source'/name
            assert hashlib.sha256(read(p)).hexdigest() == sha, (suffix, name)
        source_comparison[suffix] = {'listed_sources':len(recorded),
             'different_from_r12':[n for n in ref if recorded.get(n)!=ref[n]],
             'all_recorded_source_copies_match':True}
    freezes = {name: js(DEL/name/'SOURCE-FREEZE.json')['files_sha256'] for name in
               ['v25-r10-independent-diagnostics','v25-r12-confirmation-progress']}
    r12freeze = freezes['v25-r12-confirmation-progress']
    for name, sha in r12freeze.items():
        assert hashlib.sha256(read(DEL/'v25-r12-confirmation-progress'/name)).hexdigest() == sha
    freeze_comparison = {'r12_files':len(r12freeze), 'r12_current_files_all_match':True,
             'different_from_r10': [name for name in r12freeze if
                         freezes['v25-r10-independent-diagnostics'].get(name) != r12freeze[name]]}
    r12 = runs['49f9bf9d']
    commits = r12['ring']['last_by_event']
    updown = next(x for x in r12['native_input_receives'] if x['fields']['step']=='2' and x['fields']['status']=='1')
    upup = next(x for x in r12['native_input_receives'] if x['fields']['step']=='2' and x['fields']['status']=='0')
    http = r12['R12-web-http-evidence.json']
    derived = {'last_commit_to_up_down_guest_clock1_ns':
                    num(updown['fields']['wait_return_ns'])-commits['commit']['guest_ns'],
               'last_commit_to_up_up_guest_clock1_ns':
                    num(upup['fields']['wait_return_ns'])-commits['commit']['guest_ns'],
               'UP_request_to_End_request_browser_wall_seconds':
                    (http['stop'][0]['timestamp']-http['key'][1]['timestamp'])/1000,
               'r12_active_gate_skip_fraction_whole_run':
                    r12['ui_gate']['active']['backlog_skip']/r12['ui_gate']['active']['counts'][5],
               'all14_recorded_input_checks_identical': all(
                    x['binding_receipt']['input_checks']==r12['binding_receipt']['input_checks'] for x in runs.values()),
               'retained_tail_all_calls_paired_existing_parser':
                    not js(ROOT/r12['run']/'osd-ring-final-diag.json')['unpaired_enters_in_tail']}
    out = {'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'volume_uuid': UUID, 'scope': 'Read-only existing original FX3 evidence; no VM/guest/platform action',
           'runs':runs, 'source_comparison':source_comparison,
           'frozen22_source_comparison':freeze_comparison, 'derived_fields':derived,
           'clocks': {'ring_and_key_receive': 'guest CLOCK_MONOTONIC id=1',
                      'ui_gate_first_last_ns': 'guest clock id=7; last_ns updates only on sampled id<12 logs',
                      'timer_input_time':'widget callback input; not assumed guest CLOCK_MONOTONIC ns',
                      'qmp_elapsed_seconds':'host runner-relative monotonic elapsed',
                      'HTTP_timestamp':'browser wall milliseconds; differences only within this clock'},
           'inputs': INPUTS}
    for rel, pin in INPUTS.items():
        assert digest(ROOT/rel) == pin['sha256'], rel
    (HERE/'EVIDENCE.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
    (HERE/'INPUT-SHA256SUMS').write_text(''.join(f"{pin['sha256']}  {ROOT/rel}\n" for rel,pin in sorted(INPUTS.items())))
    print(json.dumps({'runs':list(runs), 'inputs_unchanged':len(INPUTS),
                      'source_comparison':source_comparison}, ensure_ascii=False))


if __name__ == '__main__':
    main()
