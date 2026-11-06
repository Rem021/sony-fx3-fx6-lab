"""Post-cleanup read-only audit of the single rehearsal; never starts a browser."""
import collections,difflib,socket,sys
from common import *
from dependency_gate import verify
verify('DEPENDENCY-AFTER.json')
prepared=read('SOURCE-FREEZE.json');assert len(prepared)==8
assert all(sha(HERE/f)==h for f,h in prepared.items())
assert read('PREFLIGHT-RESULT.json')['passed'] and not (HERE/'FAILURE.json').exists()
rows=[json.loads(x) for x in (HERE/'fixture-events.jsonl').read_text().splitlines()];timeline=[json.loads(x) for x in (HERE/'tool-timeline.jsonl').read_text().splitlines()]
posts=[x for x in rows if x['stage']=='HTTP_response_written' and x['method']=='POST'];requests=[x for x in rows if x['stage']=='HTTP_request']
assert collections.Counter(x['path'] for x in posts)==collections.Counter({'/api/browser-ready':1,'/api/start':1,'/api/key':2,'/api/confirm-visual':1,'/api/stop':1,'/api/final-ack':1})
keys=[x for x in posts if x['path']=='/api/key'];assert [x['HTTP_status'] for x in keys]==[409,202]
a=read('attempt-A.json');b=read('attempt-B.json');c=identity();ca=read('recovery-cancel/cancel-result.json');ar=ca['browser_result']['alarm_cancel_receipt'];armA=json.loads(read('alarm-A-arm-process.json')['stdout']);armB=json.loads(read('alarm-B-arm-process.json')['stdout'])
assert keys[0]['response']['request_id']==a['attempt_id'] and keys[0]['response']['accepted'] is False and keys[0]['response']['enqueued'] is False
assert keys[1]['response']['request_id']==b['attempt_id'] and keys[1]['response']['accepted'] is True
assert a['outcome']=='explicit_rejected_unqueued' and b['outcome']=='accepted' and a['alarm_nonce']==CFG['nonce_A'] and b['alarm_nonce']==CFG['nonce_B'] and CFG['nonce_A']!=CFG['nonce_B']
original=[x for x in rows if x['stage']=='original_submit_return_under_same_lock'];assert original[0]['pending_count']==0 and original[0]['steps']==0 and original[1]['pending_count']==1
rejection=original[0]['rejections']['records'][0];assert rejection['failed_predicates']==['sha_mismatch','generation_mismatch']
assert ca['status']=='cancelled_unqueued_alarm_only' and ca['guest_keys_sent']==ca['confirm_calls']==ca['new_alarm_calls']==0 and ca['browser_result']['no_visual_approval']
cap=read('accepted-menu-capture/capture-result.json');assert cap['status']=='qualified_screenshot_for_operator_review' and read('bounded-capture-process.json')['returncode']==0
confirm=read('explicit-confirm-receipt.json');br=confirm['browser_result'];assert confirm['status']==br['status']=='confirmed_and_cancelled'
ack=next(x for x in posts if x['path']=='/api/confirm-visual');expected=br['expected'];assert ack['HTTP_status']==200 and ack['response']['confirmed'] and ack['response']['guest_input_written'] is False
assert all(ack['response'][k]==v for k,v in expected.items())
assert expected['PNG_sha256']==cap['reference_png_sha256']==br['current_frame']['PNG_sha256'] and expected['observed_sequence']==br['current_frame']['sequence'] and expected['content_generation']==br['current_frame']['content_generation']
assert ca['host_end_ns']<read('click-B-receipt.json')['host_start_ns'] and read('validated-menu-return.json')['validation_boundary']['host_ns']<read('explicit-confirm-process.json')['start']['host_ns']
for arm,receipt,nonce,attempt in [(armA,ar,CFG['nonce_A'],a),(armB,br['cancelled'],CFG['nonce_B'],b)]:
 cur=receipt['current'];assert cur['state']=='cancelled' and cur['nonce']==nonce and cur['due_ms']==arm['current']['due_ms']==attempt['alarm_due_ms']
 assert 0<=cur['cancelled_ms']-cur['armed_ms']<20000 and cur['due_ms']==cur['armed_ms']+20000
 assert any(x['event']=='cancelled' and x['nonce']==nonce and 0<=x['elapsed_ms']<20000 for x in receipt['events'])
dispose=read('deadline-dispose.json');assert dispose['sealed'] and dispose['events'][-1]['event']=='disposed'
assert collections.Counter(x['event'] for x in dispose['events'])==collections.Counter({'installed':1,'armed':2,'cancelled':2,'disposed':1})
assert not (HERE/'dispose-not-invoked.json').exists()
# Validate each exact returned new PNG again, without displaying or calling the browser.
shots=[]
for validation,folder,kind in [('validated-recovery-return.json','recovery-review','review'),('validated-cancel-return.json','recovery-cancel','cancel'),('validated-menu-return.json','accepted-menu-capture','menu')]:
 v=read(validation);p=Path(v['screenshot_path']);assert v['validated'] and p.parent==HERE/folder and p.is_file() and not p.is_symlink() and sha(p)==v['screenshot_sha256'] and p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
 shots.append({'role':kind,'path':str(p),'file_sha256':sha(p),'bytes':p.stat().st_size,'tool_prepared_boundary':v['validation_boundary'],'actual_model_received_at':'unknown','actual_model_review_completed_at':'unknown'})
ledger=read('ledger.json');obs=[json.loads(x) for x in (HERE/'ledger-observations.jsonl').read_text().splitlines()]
assert len(ledger['attempts'])==2 and all(x['status']=='click_invoked' for x in ledger['attempts']) and len(ledger['recoveries'])==1 and ledger['recoveries'][0]['status']=='cancelled_unqueued_alarm_only'
assert all(any(any(y.get('reservation_id')==x['reservation_id'] and y['status']=='reserved_unknown' for y in snap['ledger']['attempts']) for snap in obs) for x in ledger['attempts'])
assert any(any(y['status']=='reserved_unknown' for y in snap['ledger']['recoveries']) for snap in obs)
cleanup=read('CLEANUP.json');assert not cleanup['errors'] and not cleanup['pid_alive'] and cleanup['port_closed'] and cleanup['fixture_closed']['final_ack_seen'] and not cleanup['fixture_closed']['server_thread_alive'] and cleanup['fixture_closed']['actual_guest_inputs']==0
assert json.loads(read('browser-after-close-process.json')['stdout'])['data']['active'] is False
assert next(x for x in posts if x['path']=='/api/stop')['HTTP_status']==202 and next(x for x in posts if x['path']=='/api/final-ack')['HTTP_status']==200
bp=json.loads(read('browser-before-close-process.json')['stdout'])['data']['pid'];pids=[]
for pid in [cleanup['fixture_pid'],bp]:
 try:os.kill(pid,0);alive=True
 except ProcessLookupError:alive=False
 pids.append({'pid':pid,'alive':alive})
s=socket.socket();s.settimeout(.3);code=s.connect_ex(('127.0.0.1',cleanup['port']));s.close();assert all(not x['alive'] for x in pids) and code!=0
write('PROCESS-EXIT-VERIFICATION.json',{'owned_pids':pids,'port':cleanup['port'],'connect_ex':code,'all_gone':True,'port_closed':True,'fixture_exit_status':'unknown; original preparation parent exited, no waitable child',**stamp()})
http=[]
for req in requests:
 response=next(x for x in posts if x['id']==req['id']);entry={'request':req,'response':response}
 if req['path']=='/api/key':entry['nonce']=CFG['nonce_A'] if json.loads(req['body_utf8'])['request_id']==a['attempt_id'] else CFG['nonce_B']
 if req['path']=='/api/confirm-visual':entry['nonce']=CFG['nonce_B'];entry['expected_historical_ACK']=expected
 http.append(entry)
write('HTTP-OWNERSHIP.json',http)
frames=[x for x in rows if x['stage']=='historical_fixture_publish'];write('PNG-IDENTITIES.json',{'firmware_fixture_sources':frames,'returned_browser_screenshots':shots,'prepared_screenshot':{'path':str(HERE/'prepared-page.png'),'sha256':sha(HERE/'prepared-page.png')},'ended_screenshot':{'path':str(HERE/'ended-page.png'),'sha256':sha(HERE/'ended-page.png'),'role':'cleanup only, no new approval'},'hash_not_semantic_approval':True})
def ev(stage):return next(x for x in timeline if x['stage']==stage)
def delta(first,last):return (ev(last)['host_ns']-ev(first)['host_ns'])/1e6
cancelA=next(x for x in ar['events'] if x['event']=='cancelled' and x['nonce']==CFG['nonce_A']);cancelB=next(x for x in br['cancelled']['events'] if x['event']=='cancelled' and x['nonce']==CFG['nonce_B'])
stop=next(x for x in posts if x['path']=='/api/stop');finalack=next(x for x in posts if x['path']=='/api/final-ack')
timing={'browser_performance_domain':{'documentTimeOrigin':armA['documentTimeOrigin'],'A':{'nonce':CFG['nonce_A'],'armed_ms':ar['current']['armed_ms'],'original_due_ms':ar['current']['due_ms'],'cancelled_ms':ar['current']['cancelled_ms'],'elapsed_ms':cancelA['elapsed_ms'],'due_unchanged':True},'B':{'nonce':CFG['nonce_B'],'armed_ms':br['cancelled']['current']['armed_ms'],'original_due_ms':br['cancelled']['current']['due_ms'],'cancelled_ms':br['cancelled']['current']['cancelled_ms'],'elapsed_ms':cancelB['elapsed_ms'],'due_unchanged':True},'complete_alarm_events':dispose['events'],'confirm_events':br['events']},'host_same_domain_deltas_ms':{'A_return_prepared_to_cancel_tool_entry':delta('operator_tool_reject_capture_return_prepared','operator_tool_cancel_A_entry'),'cancel_return_prepared_to_B_tool_entry':delta('operator_tool_cancel_A_return_prepared','operator_tool_accept_capture_entry'),'menu_return_prepared_to_confirm_tool_entry':delta('operator_tool_accept_capture_return_prepared','operator_tool_confirm_B_entry'),'bounded_CLI':delta('bounded-capture_enter','bounded-capture_exit'),'explicit_confirm_CLI':delta('explicit-confirm_enter','explicit-confirm_exit'),'End_to_finalACK_HTTP_responses':(finalack['host_ns']-stop['host_ns'])/1e6},'actual_model_received_at':'unknown','actual_model_review_completed_at':'unknown','note':'Return-prepared is measured before tool/image delivery; gaps include delivery, visual review and next-call scheduling; never subtract host_ns from browser performance.'}
write('OPERATOR-TIMELINE.json',{'host_tool_events':timeline,'HTTP_fixture_events':rows,'derived':timing})
compare={}
for p,start,end in [(HERE/'fixture_contract.py',1,20),(HERE/'fixture_server.py',27,46),(HERE/'operate.py',49,75),(FROZEN/'run_trial_v25_diag_r3.py',600,634),(OPS/'bounded_capture.js',69,85)]:
 lines=p.read_text().splitlines();compare[str(p)]={'sha256':sha(p),'lines':[{'line':i,'text':lines[i-1]} for i in range(start,min(end,len(lines))+1)]}
write('SOURCE-CONTRACT-COMPARISON.json',compare)
diffs=[]
for f in read('BASE-SOURCE-INPUTS.json'):
 old=Path(f);new=HERE/old.name;diffs.extend(difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True),fromfile=str(old),tofile=str(new)))
(HERE/'r21-to-r21b-local-source.diff').write_text(''.join(diffs))
counts={'key_POSTs':2,'rejected_unqueued':1,'accepted_fixture_keys':1,'recovery_cancels':1,'confirm_POSTs':1,'actual_guest_inputs':0,'explicit_operator_clicks':2,'independent_accepted_menu_visual_confirmations':1,'arms_new_unique_nonce':2,'retries':0,'same_nonce_rearms':0}
write('RESULT.json',{'outcome':'passed','scope':'single offline independent operator chain only','checks':{k:'passed' for k in ['two_targeted_no_browser_prechecks','frozen_and_old_failed_integrity_before_after','A_original_lock_409_request_match_pending0','A_new_recovery_capture_and_actual_visual_review','A_separate_cancel_same_due_under20s_no_key_confirm_rearm','separate_post_cancel_image_visual_review','B_new_nonce_explicit_operator_click_accepted','B_bounded_capture_new_regular_png_hash_identity','B_actual_complete_menu_visual_review_in_separate_tool','B_original_confirm_exact_HTTP_ACK_and_same_nonce_cancel','End_finalACK_dispose_and_owned_cleanup','reservation_and_final_ledger_evidence']},'counts':counts,'timing':timing,'identity':{'session':CFG['session'],'url':c['url'],'launch_id':c['launch_id'],'attempt_A':a['attempt_id'],'nonce_A':CFG['nonce_A'],'attempt_B':b['attempt_id'],'nonce_B':CFG['nonce_B'],'confirm_request_id':expected['request_id']},'ledger_final':ledger,'original_menu_fixture_performance_claim':False,'VM_8key_first_frame_device_FX6_not_proven':True,'preexecution_sources_unchanged':True,'preexecution_source_count':len(prepared),'next':'Coordinator decides separately authorized real VM work; this result does not grant VM execution.'})
write('AUDIT-RESULT.json',{'passed':True,'scope':'retained evidence read-only audit after cleanup','preexecution_sources_unchanged':True,'checks':'all assertions in finalize.py passed','counts':counts,**stamp()})
print(json.dumps({'outcome':'passed','counts':counts,'timing':timing,'browser_pid':bp,'fixture_pid':c['pid']},ensure_ascii=False,indent=2))
