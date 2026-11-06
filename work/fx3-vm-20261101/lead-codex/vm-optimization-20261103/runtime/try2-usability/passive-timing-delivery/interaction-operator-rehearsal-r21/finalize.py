"""Read-only evidence audit after cleanup; no browser/service/VM starts."""
import collections,socket,sys
from common import *
from dependency_gate import verify
verify('DEPENDENCY-AFTER.json')
prepared=read('SOURCE-FREEZE.json')
assert all(sha(HERE/f)==h for f,h in prepared.items())
rows=[json.loads(x) for x in (HERE/'fixture-events.jsonl').read_text().splitlines()]
tools=[json.loads(x) for x in (HERE/'tool-timeline.jsonl').read_text().splitlines()]
posts=[x for x in rows if x['stage']=='HTTP_response_written' and x['method']=='POST']
requests=[x for x in rows if x['stage']=='HTTP_request']
keys=[x for x in posts if x['path']=='/api/key'];assert len(keys)==2
assert [x['HTTP_status'] for x in keys]==[409,202]
a=read('attempt-A.json');b=read('attempt-B.json');cancel=read('recovery-cancel/cancel-result.json');ar=cancel['browser_result']['alarm_cancel_receipt'];armA=json.loads(read('alarm-A-arm-process.json')['stdout']);armB=json.loads(read('alarm-B-arm-process.json')['stdout'])
assert keys[0]['response']['request_id']==a['attempt_id'] and keys[0]['response']['accepted'] is False and keys[0]['response']['enqueued'] is False
assert keys[1]['response']['request_id']==b['attempt_id'] and keys[1]['response']['accepted'] is True
assert a['alarm_nonce']==CFG['nonce_A'] and b['alarm_nonce']==CFG['nonce_B'] and CFG['nonce_A']!=CFG['nonce_B']
assert ar['current']['state']=='cancelled' and ar['current']['due_ms']==armA['current']['due_ms']==a['alarm_due_ms']
assert ar['current']['cancelled_ms']-ar['current']['armed_ms']<20000
assert any(x['event']=='cancelled' and x['nonce']==CFG['nonce_A'] for x in ar['events'])
assert cancel['confirm_calls']==cancel['guest_keys_sent']==cancel['new_alarm_calls']==0
assert cancel['browser_result']['no_visual_approval']
assert not any(x['path']=='/api/confirm-visual' for x in requests)
original=[x for x in rows if x['stage']=='original_submit_return_under_same_lock'];assert original[0]['pending_count']==0 and original[1]['pending_count']==1
cap=read('accepted-menu-capture/capture-result.json');assert cap['status']=='no_qualified_screenshot' and not cap['screenshot_attempted'] and not cap.get('screenshot_path')
assert read('bounded-capture-process.json')['returncode']==2 and 'step_one_review_visual_state_unexpected' in cap['reason']
assert not (HERE/'validated-menu-return.json').exists() and not (HERE/'explicit-confirm-receipt.json').exists()
obs=[json.loads(x) for x in (HERE/'ledger-observations.jsonl').read_text().splitlines()]
assert all(any(x['ledger']['attempts'] and any(y.get('reservation_id')==r['reservation_id'] and y['status']=='reserved_unknown' for y in x['ledger']['attempts']) for x in obs) for r in read('ledger.json')['attempts'])
assert any(any(y['status']=='reserved_unknown' for y in x['ledger']['recoveries']) for x in obs)
cleanup=read('CLEANUP.json');assert not cleanup['pid_alive'] and cleanup['port_closed'] and cleanup['fixture_closed']['final_ack_seen'] and not cleanup['fixture_closed']['server_thread_alive']
assert json.loads(read('browser-after-close-process.json')['stdout'])['data']['active'] is False
assert [x['HTTP_status'] for x in posts if x['path']=='/api/stop']==[202]
assert [x['HTTP_status'] for x in posts if x['path']=='/api/final-ack']==[200]
owned_pids=[cleanup['fixture_pid'],json.loads(read('browser-before-close-process.json')['stdout'])['data']['pid']]
proof=[]
for pid in owned_pids:
 try:os.kill(pid,0);alive=True
 except ProcessLookupError:alive=False
 proof.append({'pid':pid,'alive':alive})
s=socket.socket();s.settimeout(.3);portcode=s.connect_ex(('127.0.0.1',cleanup['port']));s.close()
write('PROCESS-EXIT-VERIFICATION.json',{'pids':proof,'port':cleanup['port'],'connect_ex':portcode,'all_gone':all(not x['alive'] for x in proof),'port_closed':portcode!=0,'fixture_exit_status':'unknown; no waitable child after preparation parent exited',**stamp()})
assert all(not x['alive'] for x in proof) and portcode!=0
# Preserve direct source comparison with line numbers; original code is read only.
compare={}
for path,start,end in [(HERE/'fixture_server.py',25,43),(FROZEN/'run_trial_v25_diag_r3.py',600,634),(OPS/'bounded_capture.js',69,86),(FROZEN/'pending_visual_v20.py',28,40),(FROZEN/'tests/test_helper_browser_integration.py',65,77)]:
 lines=path.read_text().splitlines();compare[str(path)]={'source_sha256':sha(path),'lines':[{'line':i,'text':lines[i-1]} for i in range(start,min(end,len(lines))+1)]}
write('STATE-CONTRACT-COMPARISON.json',compare)
http=[]
for r in requests:
 response=next(x for x in posts if x['id']==r['id']);body=json.loads(r['body_utf8']);entry={'request':r,'response':response}
 if r['path']=='/api/key':entry['attributed_nonce']=a['alarm_nonce'] if body['request_id']==a['attempt_id'] else b['alarm_nonce']
 http.append(entry)
write('HTTP-OWNERSHIP.json',http)
frames=[x for x in rows if x['stage']=='historical_fixture_publish']
shotfiles=['prepared-page.png','recovery-review/review-page.png','recovery-cancel/current-after-cancel.png','ended-page.png']
identities={'firmware_fixture_pngs':frames,'browser_screenshots':[{'path':str(HERE/f),'sha256':sha(HERE/f),'bytes':(HERE/f).stat().st_size,'role':'cleanup only; no qualified operator approval' if f=='ended-page.png' else 'preparation' if f=='prepared-page.png' else 'actually returned in corresponding same tool result'} for f in shotfiles],'accepted_menu_qualified_screenshot':None,'no_hash_is_visual_approval':True};write('PNG-IDENTITIES.json',identities)
# Same-origin host ns deltas only; browser performance elapsed is kept separate.
def eventof(stage):return next(x for x in tools if x['stage']==stage)
recovery_return=eventof('operator_tool_reject_capture_return_prepared');cancel_entry=eventof('operator_tool_cancel_A_entry');cancel_return=eventof('operator_tool_cancel_A_return_prepared');Bentry=eventof('operator_tool_accept_capture_entry')
stop=next(x for x in posts if x['path']=='/api/stop');finalack=next(x for x in posts if x['path']=='/api/final-ack')
failproc=read('bounded-capture-process.json')
timing={'browser_performance_domain':{'origin':armA['documentTimeOrigin'],'nonce_A':{'armed_ms':armA['current']['armed_ms'],'due_ms':armA['current']['due_ms'],'cancelled_ms':ar['current']['cancelled_ms'],'elapsed_ms':cancel['browser_result']['elapsed_ms'],'due_unchanged':True,'complete_cancel_events':ar['events']},'nonce_B':{'armed_ms':armB['current']['armed_ms'],'original_due_ms':armB['current']['due_ms'],'confirmed_or_cancelled':False,'last_recorded_state':cap['before_eval']['diagnostics']['alarm_state'],'remaining_ms_at_capture_failure':cap['before_eval']['diagnostics']['remaining_ms'],'closed_document_before_original_due':True}},'host_same_domain_deltas_ms':{'recovery_tool_return_prepared_to_next_cancel_tool_entry':(cancel_entry['host_ns']-recovery_return['host_ns'])/1e6,'cancel_tool_return_prepared_to_next_B_tool_entry':(Bentry['host_ns']-cancel_return['host_ns'])/1e6,'bounded_capture_child_process':(failproc['end']['host_ns']-failproc['start']['host_ns'])/1e6,'bounded_capture_failure_to_End_HTTP_response':(stop['host_ns']-failproc['end']['host_ns'])/1e6,'End_to_finalACK_HTTP_response':(finalack['host_ns']-stop['host_ns'])/1e6},'model_image_received_at':'unknown','model_review_completed_at':'unknown','timing_note':'Tool-return-prepared is instrumented before image encoding/tool delivery, not actual model receipt; gaps include tool delivery, review, next-call scheduling; never subtract host_ns from performance_ms.'}
write('OPERATOR-TIMELINE.json',{'host_tool_events':tools,'http_and_fixture_events':rows,'derived':timing})
write('FAILURE.json',{'outcome':'failed','stage':'B accepted MENU bounded capture','cause':'Controlled fixture called require_visual_review(1, visual_pending, True), violating original runner final-review state contract','tool_exit':2,'exact_reason':cap['reason'],'retry_count':0,'actual_confirm_calls':0,'cleanup_dispose':'refused because B alarm remained armed; no retry/cancel invented','failure_cleanup_dispatch':'operate.run_action was imported in the tool script, so its __main__ cleanup handler did not run; operator sent next dedicated cleanup call after reading failure','coordinator_instruction_message':'msg_cb4489e73594',**stamp()})
result={'outcome':'failed','scope':'one offline independent operator rehearsal; no VM/guest','checks':{'frozen_dependency_integrity':'passed','two_explicit_clicks_one_reject_one_accept':'passed','A_original_lock_rejection_request_attribution_pending0':'passed','A_capture_new_PNG_returned_and_actually_reviewed':'passed','A_separate_cancel_same_nonce_due_elapsed_under20s_no_confirm_no_key_no_rearm':'passed','A_new_post_cancel_PNG_returned_separate_visual_review':'passed','B_fresh_nonce_explicit_click_accepted':'passed','B_bounded_qualified_capture':'failed','B_independent_complete_menu_visual_confirmation':'not_performed','B_original_explicit_confirm_historical_ACK_and_cancel':'not_performed','End_and_finalACK':'passed','deadline_dispose':'failed_refused_B_still_armed','own_browser_service_pid_port_cleanup':'passed'},'counts':{'explicit_operator_clicks':2,'HTTP_key_posts':2,'rejected_unqueued':1,'accepted_fixture_keys':1,'unqueued_recoveries':1,'actual_guest_inputs':0,'confirm_visual_posts':0,'independent_accepted_menu_visual_confirmations':0,'new_nonce_arms':2,'same_nonce_rearm':0,'retries':0},'timing':timing,'ledger_final':read('ledger.json'),'local_preexecution_sources_unchanged':True,'next':'Coordinator must separately authorize a corrected fixture assignment; preserve this failed round and frozen helpers.'}
write('RESULT.json',result)
write('AUDIT-RESULT.json',{'evidence_audit_passed':True,'rehearsal_outcome':'failed','assertions_scope':'read-only retained evidence only; no retry or new service/browser','source_freeze_preexecution_count':len(prepared),**stamp()})
print(json.dumps({'outcome':result['outcome'],'counts':result['counts'],'timing':timing},ensure_ascii=False,indent=2))
