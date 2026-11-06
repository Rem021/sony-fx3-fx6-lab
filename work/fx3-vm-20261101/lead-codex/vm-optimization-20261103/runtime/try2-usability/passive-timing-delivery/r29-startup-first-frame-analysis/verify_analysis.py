#!/usr/bin/env python3
"""Verify analysis receipts and raw offsets without runtime imports or mutation."""
import datetime as dt, hashlib, json
from pathlib import Path
P=Path(__file__).resolve().parent
inputs=json.loads((P/'INPUTS.json').read_text())
checked=[]
for row in inputs['files']:
    b=Path(row['path']).read_bytes()
    assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],row['path']
    assert row['unchanged_after_analysis']
    checked.append(row['path'])
proof=json.loads((P/'COMPARISON.json').read_text())
assert all(all(v.values()) for v in proof['unchanged_platform_and_startup_code'].values())
coordinate=json.loads((P.parent/'r29-coordinator-qmp-pause-accounting.json').read_text())
coordinator={x['run']:x for x in coordinate['runs']}
checks=[]
for n in ['r26','r26b','r28']:
    e=json.loads((P/(n+'-EVIDENCE.json')).read_text());raw=(Path(e['summary']['run'])/'serial.log').read_bytes()
    assert e['ring']['header_request_count']=={'r26':178,'r26b':215,'r28':397}[n]
    assert e['ring']['header_matched_empty_success_responses']==e['ring']['header_request_count']
    assert e['qmp_pause_accounting']['completed_pairs']==coordinator[Path(e['summary']['run']).name]['completed_pairs']
    for marker in e['serial_markers'].values():
        for r in marker.get('first',[])+marker.get('last',[]):
            off=r['byte_offset'];text=r['text'].encode()
            assert raw[off:off+len(text)]==text
            assert raw[:off].count(b'\n')+1==r['LF_line']
    assert e['summary']['original_backup_readback']['before_AP_bootin_marker']
    assert e['summary']['original_backup_readback']['native_file_seen_and_module_load0']
    checks.append({'run':n,'raw_serial_offsets_and_LF_lines_match':True,'header_id_matching':True,'pause_event_pairing_matches_coordinator':True})
e=json.loads((P/'r28-EVIDENCE.json').read_text());t=json.loads((P/'TIMELINE.json').read_text())
b=t['r28_end_boundary']
assert b['last_observed_zero_header_host_monotonic']<b['End_tool_start_host_monotonic']<b['first_observed_positive_header_host_monotonic']<b['first_pixel_publication_host_monotonic']
assert e['http']['first_status_ready'] is None and e['http']['first_status_frame']['phase']=='stopping'
assert e['http']['POST_counts']['start']==1 and e['http']['POST_counts']['stop']==1
assert not any('key' in k for k in e['http']['POST_counts'])
assert e['summary']['receipt']['render_pass'] is False and e['summary']['receipt']['standby_ready'] is False
assert e['summary']['receipt']['render_valid_at_end'] is True
assert e['serial_markers']['UI_WIRE_low16_1004']['first'][0]['fields']['tag1']=='0x21004'
assert e['UI_original_paused_published_counters']['time_pass']==2
assert e['UI_original_paused_published_counters']['backlog_skip']==4493
r={'verified_UTC':dt.datetime.now(dt.timezone.utc).isoformat(),'outcome':'read_only_analysis_passed_root_cause_unresolved',
   'original_input_count':len(checked),'all_consumed_original_inputs_unchanged':True,'checks':checks,
   'r28_End_boundary_straddles_first_commit_observation':True,'late_frame_does_not_retroqualify':True,
   'r28_start_count':1,'r28_key_POST_count':0,
   'analysis_actions':{'VM_or_Start':0,'browser_or_service':0,'runtime_import':0,'candidate_or_platform_change':0},
   'cleanup':'No owned VM, browser or service was created; only foreground read-only analysis processes used.',
   'limits':'No causal root fix or new runtime acceptance claimed; historical sealed samples remain failed overall.'}
(P/'VERIFY.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(r,ensure_ascii=False,indent=2))
