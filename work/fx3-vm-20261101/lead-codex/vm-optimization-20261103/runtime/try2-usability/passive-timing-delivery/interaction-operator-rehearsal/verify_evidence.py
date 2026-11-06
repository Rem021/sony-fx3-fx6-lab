#!/usr/bin/env python3
"""Offline audit of the one failed rehearsal; never starts browser/server/VM."""
import collections, datetime, hashlib, json
from pathlib import Path
H=Path(__file__).resolve().parent;D=H.parent
events=[json.loads(l) for l in (H/'fixture-events.jsonl').read_text().splitlines()]
http=[e for e in events if e['event']=='HTTP_reply_written']
posts=[e for e in http if e['request_method']=='POST']
one=lambda path:next(e for e in posts if e['path']==path)
key=one('/api/key');stop=one('/api/stop');final=one('/api/final-ack')
counts=dict(collections.Counter(e['path'] for e in posts))
assert counts=={'/api/browser-ready':1,'/api/start':1,'/api/key':1,'/api/stop':1,'/api/final-ack':1},counts
assert key['HTTP_status']==stop['HTTP_status']==202 and final['HTTP_status']==200
capture=json.loads((H/'menu-capture-01/capture-result.json').read_text())
assert capture['status']=='no_qualified_screenshot' and not capture['screenshot_attempted']
assert capture['reason']=='Error: phase_or_input_gate_not_ready'
assert capture['confirm_calls']==capture['alarm_mutations']==capture['guest_keys_sent']==0
assert not (H/'explicit-confirm-receipt.json').exists() and not (H/'manual-confirm-invocation.json').exists()
arm=json.loads((H/'deadline-arm.json').read_text());alarm=json.loads(json.loads((H/'cleanup-status.json').read_text())['stdout'])
assert arm['current']['nonce']==alarm['current']['nonce'] and arm['current']['due_ms']==alarm['current']['due_ms']
assert alarm['current']['state']=='expired' and alarm['sealed']
assert [e['event'] for e in alarm['events']]==['installed','armed','already_stopping_or_disabled']
assert arm['deadline_ms']==alarm['deadline_ms']==20000
clean=json.loads((H/'CLEANUP.json').read_text())
assert clean['PID_absent'] and clean['port_closed'] and clean['browser']['data']['active'] is False
assert clean['browser']['data']['pid'] is None
closed=next(e for e in events if e['event']=='fixture_server_closed')
assert not closed['server_thread_alive'] and closed['final_ack_seen'] and closed['snapshot']['phase']=='finished'
key_enter=next(e for e in events if e['event']=='fake_menu_handler_enter')
publish=next(e for e in events if e['event']=='fixture_publish_complete')
cap_pre=next(e for e in capture['timeline'] if e['stage']=='before_eval_enter')
status_before=max((e for e in http if e['path']=='/api/status' and e['host_monotonic']<key_enter['host_monotonic']),key=lambda e:e['host_monotonic'])
status_after=min((e for e in http if e['path']=='/api/status' and e['host_monotonic']>key_enter['host_monotonic']),key=lambda e:e['host_monotonic'])
assert status_before['host_monotonic']<key_enter['host_monotonic']<cap_pre['monotonic']<status_after['host_monotonic']
pins=json.loads((H/'DEPENDENCY-VERIFICATION.json').read_text())
after={}
for folder,p in pins['results'].items():
    base=D/folder
    for file,h in p['pins'].items():assert hashlib.sha256((base/file).read_bytes()).hexdigest()==h
    files=json.loads((base/'SOURCE-FREEZE.json').read_text())['files']
    for file,h in files.items():assert hashlib.sha256((base/file).read_bytes()).hexdigest()==h
    deps=json.loads((base/'DEPENDENCIES.json').read_text())
    for e in deps.values():assert hashlib.sha256(Path(e['path']).read_bytes()).hexdigest()==e['sha256']
    after[folder]={'source_files':len(files),'dependency_files':len(deps),'unchanged':True}
result={'overall':'failed','scope':'single simulated operator rehearsal; no guest evidence',
 'post_counts':counts,'accepted_fake_MENU_keys':1,'actual_guest_keys':0,'confirm_CLI_invocations':0,
 'qualified_target_screenshot':'failed','operator_target_review':'not_reached','explicit_confirm':'not_invoked',
 'same_nonce_cancel':'not_reached','cleanup':'passed','dependency_integrity_after':after,
 'nonce':arm['current']['nonce'],'due_ms':arm['current']['due_ms'],'arm_performance_ms':arm['current']['armed_ms'],
 'key_to_Stop_HTTP_reply_host_seconds':stop['host_monotonic']-key['host_monotonic'],
 'capture_eval_enter_after_key_handler_enter_seconds':cap_pre['monotonic']-key_enter['host_monotonic'],
 'capture_command_elapsed_ms':capture['host_elapsed_ms'],'browser_wait_before_refusal_ms':capture['before_eval']['waited_ms'],
 'specified_target_delay_seconds':7.0,'fake_MENU_handler_to_target_publish_host_seconds':publish['host_monotonic']-key_enter['host_monotonic'],
 'clocked_events':{'key':key,'Stop':stop,'finalACK':final,'last_status_reply_before_key':status_before,'first_status_reply_after_key':status_after,
                   'late_complete_PNG_publication':publish},
 'model_image_receive_UTC':None,'model_target_review_complete_UTC':None,
 'unknowns':['No direct failure-time dump of individual PAGE lexical variables; check group is generic',
             'Model image receipt/review clock unavailable; no qualified target image was returned',
             'Explicit-confirm runtime and end-to-end completion remain untested by this rehearsal']}
(H/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='clocked_events'},ensure_ascii=False,indent=2))
