#!/usr/bin/env python3
import json,statistics
from datetime import datetime
from pathlib import Path
R=Path(__file__).resolve().parent; H=json.loads((R/'receipts/har-transitions.json').read_text()); T=json.loads((R/'receipts/command-entry-timing.json').read_text()); P=json.loads((R/'receipts/page-helper-replay.json').read_text()); V=json.loads((R/'receipts/visual-correction.json').read_text())
times=[datetime.fromisoformat(s['utc'].replace('Z','+00:00')) for s in H['status_frames']]; deltas=[(b-a).total_seconds()*1000 for a,b in zip(times,times[1:])]
value={'schema':'fx3-r49-frame-admission-findings-v1','task':'task_1570d1fe8f1b','dispatch':'ctx_8c5041207422',
 'runtime_contact':False,'new_vm_browser_server_qmp_guest':False,'diagnosis_complete':True,'menu_pass':False,
 'facts':{'post_paths':[p['url'] for p in H['post_paths']],'api_key_post_count':H['api_key_post_count'],
  'attempt1':{'clicked':H['attempts'][0]['clicked_frame'],'preflight':H['attempts'][0]['preflight_status']['frame'],
   'last_tick_to_click_ms':H['attempts'][0]['last_tick_to_click_ms'],'click_to_preflight_ms':H['attempts'][0]['click_to_preflight_ms'],
   'identity_ok':H['attempts'][0]['identity_ok_from_click_receipt'],'lifecycle_ok':H['attempts'][0]['lifecycle_ok_from_click_snapshot'],
   'failing_frame_terms':H['attempts'][0]['failing_frame_terms'],'outcome':H['attempts'][0]['outcome'],'frame_terms':H['attempts'][0]['frame_terms']},
  'attempt2':{'clicked':H['attempts'][1]['clicked_frame'],'preflight':H['attempts'][1]['preflight_status']['frame'],
   'last_tick_to_click_ms':H['attempts'][1]['last_tick_to_click_ms'],'click_to_preflight_ms':H['attempts'][1]['click_to_preflight_ms'],
   'identity_ok':H['attempts'][1]['identity_ok_from_click_receipt'],'lifecycle_ok':H['attempts'][1]['lifecycle_ok_from_click_snapshot'],
   'failing_frame_terms':H['attempts'][1]['failing_frame_terms'],'outcome':H['attempts'][1]['outcome'],'frame_terms':H['attempts'][1]['frame_terms']},
  'status_count':H['status_count'],'status_delta_ms':{'min':min(deltas),'median':statistics.median(deltas),'max':max(deltas),'count':len(deltas)},
  'actual_page_replay':{'canonical_sha256':P['canonical_sha256'],'helper_sha256':P['helper_sha256'],'cases':P['cases'],'negatives':P['negatives']},
  'visual_correction':V,'command_entry_timing':T},
 'branch':{'name':'PAGE click handler freshness OR (canonical PAGE lines 304-305)','reason_label':'preflight_identity_or_lifecycle_changed',
  'actual_failing_terms':H['attempts'][0]['failing_frame_terms'],'identity_lifecycle_terms_false':H['attempts'][0]['identity_lifecycle_terms'],
  'identity_ok':H['attempts'][0]['identity_ok_from_click_receipt'],'lifecycle_ok':H['attempts'][0]['lifecycle_ok_from_click_snapshot'],
  'note':'The reason string is combined; actual failing terms are frame freshness only: preflight SHA inequality, preflight content_generation inequality, !frameLoadedFor(preflight).'},
 'classification':{'frame_content_changed':True,'frame_generation_changed':True,'frame_sequence_changed':True,
  'steps_phase_ready_busy_review_error_render_changed':False,'launch_run_document_timeorigin_identity_changed':False,
  'detail':'PNG SHA e014->2914; content_generation +1; sequence +4/+8; steps=0, phase=ready, ready=true, busy=false, review_required=false, error=null, render_valid=true, same launch/run/document/timeOrigin; identity/lifecycle terms false.'},
 'sampling_and_two_requests':{'page_tick_ms':400,'last_tick_age_before_click_ms':{'attempt1':H['attempts'][0]['last_tick_to_click_ms'],'attempt2':H['attempts'][1]['last_tick_to_click_ms']},
  'click_snapshot_to_preflight_ms':{'attempt1':H['attempts'][0]['click_to_preflight_ms'],'attempt2':H['attempts'][1]['click_to_preflight_ms']},
  'description':'Host 26-check preflight reads PAGE lastStatus/displayed from last tick (up to 400 ms old); PAGE click handler then issues a fresh /api/status and sees a newer frame. The two observations do not check the same frame; the second is intentionally fresh and catches the gap.'},
 'minimal_improvement_design':[
  {'id':'obs_v2','change':'Record last_tick_frame, fresh_preflight_status_frame, frame_loaded_for_preflight and exact predicate booleans in the click receipt.','policy_change':False,'semantic_change':False,'implemented':False},
  {'id':'preclick_stability','change':'Before b.click(), require one fresh /api/status sample whose frame identity equals the PAGE displayed frame (or a short bounded stable-frame hold), then click; keep PAGE freshness, no retry, within 60s.','policy_change':True,'semantic_change':'timing/operator budget; not visual confirmation or input evidence','implemented':False},
  {'id':'new_frame_notice','change':'On freshness refusal, explicitly present the new frame and require operator re-click; never auto-post.','policy_change':False,'semantic_change':False,'implemented':False}],
 'rejected_shortcuts':['remove/reduce freshness','whitelist specific SHAs/NO CARD blink/known generations','auto-pass on stable hash','infinite/automatic retry','merge pin/confirm or auto visual pass'],
 'unknown':['exact native/OSD cause of e014->2914','whether NO CARD overlay difference caused it','raw frame-pixel comparison','exact guest-entry timestamp','phases.first_kinds cleanup serial offset / interaction cutoff','command-entry to guest-entry offset','CPU/FIFO idle or HTTP latency from adjacent guest/host/browser clocks'],
 'correction':'Coordinator actual view: recovery-before has no NO CARD; initial and recovery-after have NO CARD. Old r48 blanket "all three NO CARD" is imprecise; old sealed files unchanged. The visual difference is not proof of native flicker root cause.',
 'fact_vs_inference':{'fact':['HAR only has start/stop/final-ack POST; no /api/key','both click snapshots passed identity/lifecycle','fresh preflight frame differed in SHA/gen/seq','three frame-freshness terms true','actual PAGE+helper replay reproduces not_posted with zero API key posts','wrong identity/expired/accepted negatives refused'],'inference':['page tick snapshot is stale by up to one 400 ms tick','the two status observations amplify the race','frame content changed in the click-to-preflight window'],'not_proven':['native flicker/NO CARD causality','guest CPU/FIFO/HTTP latency','that pre-click stabilization would pass','that any code change is authorized']},
 'receipts':{'har':'receipts/har-transitions.json','replay':'receipts/page-helper-replay.json','timing':'receipts/command-entry-timing.json','visual':'receipts/visual-correction.json'}}
(R/'receipts/frame-admission-findings.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'branch':value['branch']['name'],'median_status_delta_ms':value['facts']['status_delta_ms']['median'],'receipt':str(R/'receipts/frame-admission-findings.json')}))
