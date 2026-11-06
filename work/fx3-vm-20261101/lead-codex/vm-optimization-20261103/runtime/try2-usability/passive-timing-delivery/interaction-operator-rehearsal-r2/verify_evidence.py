#!/usr/bin/env python3
"""Audit only existing rehearsal evidence; no browser/server/guest invocation."""
import collections,hashlib,json
from pathlib import Path
from dependency_gate import verify
from capture_validation import validate_capture
H=Path(__file__).resolve().parent
read=lambda p:json.loads((H/p).read_text())
config=read('fixture.json');cap=read('menu-capture-01/capture-result.json')
process=read('bounded-capture-process.json')
validated=validate_capture(process['returncode'],process['stdout'],H/'menu-capture-01')
assert validated=={k:v for k,v in read('validated-image-return.json').items() if k!='return_boundary'}
assert cap['confirm_calls']==cap['alarm_mutations']==cap['guest_keys_sent']==0
before=cap['before_eval']['before'];after=cap['after_eval']
assert after['qualified'] and not after['failed_checks']
assert before['png_sha256']==after['png_sha256']=='60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292'
assert before['content_generation']==after['content_generation']==2
assert before['sequence']<=after['sequence'] and after['remaining_ms']>=8000
confirm=read('explicit-confirm-receipt.json');br=confirm['browser_result']
assert confirm['status']==br['status']=='confirmed_and_cancelled' and br['click_invoked']
assert confirm['retries']==confirm['guest_keys_sent_by_helper']==0
arm=read('deadline-arm.json');cancel=br['cancelled']
assert arm['current']['nonce']==cancel['current']['nonce']==config['nonce']
assert arm['current']['due_ms']==cancel['current']['due_ms']==before['due_ms']==after['alarm_due_ms']
assert cancel['current']['state']=='cancelled' and arm['deadline_ms']==cancel['deadline_ms']==20000
cancel_event=next(x for x in cancel['events'] if x['event']=='cancelled')
assert cancel_event['elapsed_ms']<20000
assert sum(x['event']=='armed' for x in cancel['events'])==1 and sum(x['event']=='cancelled' for x in cancel['events'])==1
assert all(x['event'] not in ['end_click','expired'] for x in cancel['events'])
http=read('HTTP-confirm-visual.json')['data'];body=json.loads(http['responseBody']);request=json.loads(http['postData'])
assert http['method']=='POST' and http['status']==200 and body['confirmed'] and body['guest_input_written'] is False
expected=br['expected']
assert all(request[k]==body[k]==expected[k] for k in expected)
assert br['current_frame']['PNG_sha256']==before['png_sha256'] and br['current_frame']['content_generation']==before['content_generation']
events=[json.loads(s) for s in (H/'fixture-events.jsonl').read_text().splitlines()]
posts=[x for x in events if x['event']=='HTTP_reply_written' and x['request_method']=='POST']
counts=dict(collections.Counter(x['path'] for x in posts))
assert counts=={'/api/browser-ready':1,'/api/start':1,'/api/key':1,'/api/confirm-visual':1,'/api/stop':1,'/api/final-ack':1},counts
assert next(x for x in posts if x['path']=='/api/key')['HTTP_status']==202
assert next(x for x in posts if x['path']=='/api/confirm-visual')['HTTP_status']==200
assert next(x for x in posts if x['path']=='/api/stop')['HTTP_status']==202
assert next(x for x in posts if x['path']=='/api/final-ack')['HTTP_status']==200
closed=next(x for x in events if x['event']=='fixture_server_closed')
assert closed['snapshot']['phase']=='finished' and closed['final_ack_seen'] and not closed['server_thread_alive']
cleanup=read('CLEANUP.json')
assert cleanup['PID_absent'] and cleanup['port_closed'] and cleanup['browser']['data']['active'] is False and cleanup['browser']['data']['pid'] is None
dispose=read('deadline-dispose.json');assert dispose['exit_code']==0 and json.loads(dispose['stdout'])['sealed']
prep=read('PREPARATION-RECEIPT.json')
for p,sha in prep['prepared_source_hashes'].items():assert hashlib.sha256((H/p).read_bytes()).hexdigest()==sha,p
assert prep['local_fake_CLI_checks']['passed'] and len(prep['local_fake_CLI_checks']['cases'])==5
dependencies=verify()
timeline=read('operator-capture-timeline.json');point=lambda stage:next(x for x in timeline if x['stage']==stage)
capture_point=lambda stage:next(x for x in cap['timeline'] if x['stage']==stage)
manual=read('manual-confirm-invocation.json')
key=next(x for x in posts if x['path']=='/api/key');stop=next(x for x in posts if x['path']=='/api/stop')
pub=next(x for x in events if x['event']=='fixture_publish_complete')
fake=next(x for x in events if x['event']=='fake_menu_handler_enter')
result={'overall':'passed','scope':'ONE simulated original PAGE/TrialState operator chain only; no product/VM/guest acceptance',
 'accepted_fake_MENU_keys':1,'actual_guest_keys':0,'confirm_CLI_invocations':1,'confirm_POST_count':1,'HTTP_confirmation':200,
 'confirm_request_id':expected['request_id'],'nonce':config['nonce'],'original_due_ms':arm['current']['due_ms'],
 'arm_to_cancel_page_elapsed_ms':cancel_event['elapsed_ms'],'margin_at_cancel_page_ms':20000-cancel_event['elapsed_ms'],
 'capture_wait_page_ms':cap['before_eval']['waited_ms'],'capture_function_host_ms':cap['host_elapsed_ms'],
 'bounded_CLI_call_host_ms':1000*(point('bounded_capture_CLI_return')['host_monotonic']-point('bounded_capture_CLI_enter')['host_monotonic']),
 'screenshot_host_ms':1000*(capture_point('screenshot_exit')['monotonic']-capture_point('screenshot_enter')['monotonic']),
 'capture_return_preparation_to_manual_confirm_entry_host_ms':1000*(manual['host_monotonic_enter']-point('validated_tool_image_return_preparation_boundary')['host_monotonic']),
 'explicit_CLI_host_ms':1000*(confirm['host_monotonic_return']-confirm['host_monotonic_invoked']),
 'manual_wrapper_host_ms':1000*(manual['host_monotonic_return']-manual['host_monotonic_enter']),
 'specified_fake_target_delay_seconds':7.0,'fake_handler_to_target_publish_host_seconds':pub['host_monotonic']-fake['host_monotonic'],
 'key_to_End_HTTP_reply_host_seconds':stop['host_monotonic']-key['host_monotonic'],
 'before':before,'after':after,'post_counts':counts,'dependencies_after':dependencies,
 'screenshot_file_sha256':validated['screenshot_file_sha256'],'firmware_png_sha256':validated['firmware_png_sha256'],
 'page_state_transitions':[x for x in cap['before_eval']['events'] if x['kind']=='state_transition'],
 'model_received_image_UTC':None,'model_review_completed_UTC':None,
 'unknowns':['Model image reception/semantic review completion clocks unavailable; boundary interval includes tool/image return, model work and dispatch',
             'This run did not exercise accepted_menu_waiting_for_status transition; first sampled state was ready_loaded_review',
             'Single fixture success does not prove VM/menu correctness, repeatability or hard realtime deadlines']}
(H/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['before','after','page_state_transitions']},ensure_ascii=False,indent=2))
