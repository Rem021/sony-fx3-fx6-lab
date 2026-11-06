"""Read-only attribution of measured boundaries; no model-time or firmware-completion inference."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;D=ROOT.parent;B=D/'r26b-vm-93b3e243da6f'
save=lambda n,v:(ROOT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
v=json.loads((B/'STEP1-TIMELINE.json').read_text());index=json.loads((B/'TOOL-RETURN-INDEX.json').read_text());events={x['stage']:x for x in v['operator_events']}
rows=[]
for r in index:
 a=r['invocation']['action'];p=r['process'];entry=events.get('operator_tool_'+a+'_entry');ret=events.get('operator_tool_'+a+'_return_prepared')
 row={'action':a,'includes_failure_cleanup':p['returncode']!=0,'adapter_child_seconds':(p['wall_end_ns']-p['wall_start_ns'])/1e9,'child_code':p['returncode']}
 if entry and ret:
  row.update(wrapper_entry_to_return_seconds=(ret['host_ns']-entry['host_ns'])/1e9,
             child_launch_to_wrapper_entry_seconds=(__import__('datetime').datetime.fromisoformat(entry['UTC']).timestamp()*1e9-p['wall_start_ns'])/1e9,
             wrapper_return_to_child_exit_seconds=(p['wall_end_ns']-__import__('datetime').datetime.fromisoformat(ret['UTC']).timestamp()*1e9)/1e9)
 rows.append(row)
g1=v['intervals']['click_return_to_observe_entry_seconds'];g2=v['intervals']['observe_return_to_pin_entry_seconds'];click=next(x['adapter_child_seconds'] for x in rows if x['action']=='click');observe=next(x['adapter_child_seconds'] for x in rows if x['action']=='observe')
# Conditional budget scenario: eliminate the extra observe and its entire human/tool gap, but keep two required independent image-review turns.
arm=json.loads(v['arm_tool']['stdout']);arm_epoch_ms=arm['documentTimeOrigin']+arm['current']['armed_ms'];ret_epoch_ms=__import__('datetime').datetime.fromisoformat(events['operator_tool_click_return_prepared']['UTC']).timestamp()*1000
armed_to_observation_return=(ret_epoch_ms-arm_epoch_ms)/1000
lo=armed_to_observation_return+g1+g2
save('HISTORICAL-BUDGET.json',{'original_alarm_seconds':20,'source':'r26b immutable host/process timeline','child_rows':rows,'observed_return_to_next_entry_seconds':[g1,g2],
 'sum_two_observed_gaps_seconds':g1+g2,'pin_entry_after_arm_source_seconds':v['pin_entry_after_arm_wall_seconds'],
 'armed_to_first_wrapper_observation_return_seconds':armed_to_observation_return,'conditional_single_observation_two_review_gap_budget_seconds':lo,'conditional_over_20_seconds':lo-20,
 'bound_assumptions':'Use the two observed wrapper-boundary gaps as representative required observation-review and fixed-image-review gaps; delete extra observe; assign zero pin+confirm cost and zero transport beyond measured gaps; not a prediction or exact model duration.',
 'unknown':['tool image serialization/delivery completion','model image receive time','model review completion','scheduler delay','exact cost of the extra functions.wait','real pin and confirm duration because neither completed'],
 'yield_evidence':json.loads((B/'OPERATOR-TOOL-CALL-EVIDENCE.json').read_text())['functions_yield_wait'],
 'claim':'No reasonable headroom at r26b observed call-gap level under these assumptions; not a universal lower bound on all future model calls.'})
groups=[]
for g in ('group-a','group-b'):
 files=[ROOT/'evidence'/g/(a+'-measurement.json') for a in ('click','pin','confirm')]
 if not all(p.exists() for p in files):continue
 calls=[json.loads(p.read_text()) for p in files]
 spans=[(n['entry']['epoch_ms']-p['image_end']['epoch_ms'])/1000 for p,n in zip(calls,calls[1:])]
 duration=(calls[-1]['host_finish']['epoch_ms']-calls[0]['entry']['epoch_ms'])/1000
 sumchild=sum((x['child_end']['perf_ms']-x['child_begin']['perf_ms'])/1000 for x in calls)
 group={'group':g,'history_only':True,'calls':calls,'observed_inter_call_spans_seconds':spans,'measured_node_entry_to_confirm_finish_seconds':duration,'child_total_seconds':sumchild,
        'unallocated_beyond_child_and_two_gaps_seconds':duration-sumchild-sum(spans),
        'replace_replay_click_with_r26b_click_seconds':duration-(calls[0]['child_end']['perf_ms']-calls[0]['child_begin']['perf_ms'])/1000+click,
        'performance_time_origins_ms':[x['entry'].get('perf_time_origin_ms') for x in calls],'cross_call_clock':'epoch_ms from origin+now; wall Date_ms recorded separately; cross-origin perf_ms never subtracted',
        'boundary':'Between image_end and next Node entry includes tool serialization/delivery, model/scheduler and wrapper; not separable model thinking time.',
        'VM_or_original_action':False,'20s_VM_pass':False}
 groups.append(group)
if groups:
 g=groups[-1];spans=g['observed_inter_call_spans_seconds'];gap_sum=sum(spans)
 timing=json.loads((D/'r25-coordinator-menu-observation-timing.json').read_text())
 longest=max(timing['rows'],key=lambda r:r['HTTP_observation_gap_ms'])
 scenarios=[]
 for sample_arm_seconds in (4.5,5.0):
  subtotal=sample_arm_seconds+gap_sum
  scenarios.append({'first_observation_available_at_arm_seconds':sample_arm_seconds,'subtotal_before_real_pin_confirm_and_other_tail_seconds':subtotal,'remaining_for_real_pin_confirm_and_other_tail_seconds':20-subtotal})
 cost=json.loads((D/'r27-coordinator-historical-pin-confirm-cost.json').read_text())
 known_components=[{'step':r['step'],'pin_post_tail_plus_confirm_guard_helper_seconds':r['pin_POST_to_capture_return_wall_seconds']+r['confirm_helper_seconds']+r['confirm_current_guard_seconds']} for r in cost['rows']]
 component_min=min(x['pin_post_tail_plus_confirm_guard_helper_seconds'] for x in known_components)
 component_max=max(x['pin_post_tail_plus_confirm_guard_helper_seconds'] for x in known_components)
 key_post=next(r for r in json.loads((B/'HTTP-POST-ORIGINAL-BODIES.json').read_text()) if r['endpoint']=='key')
 key_epoch_ms=__import__('datetime').datetime.fromisoformat(key_post['UTC_request_start'].replace('Z','+00:00')).timestamp()*1000
 arm_to_key=(key_epoch_ms-arm_epoch_ms)/1000
 for row in scenarios:
  row['with_known_r25_tail_components_range_seconds']=[row['subtotal_before_real_pin_confirm_and_other_tail_seconds']+component_min,row['subtotal_before_real_pin_confirm_and_other_tail_seconds']+component_max]
 # Distinguish sampling start at5s from the more optimistic image-available-by5s assumption.
 later_start=5+observe+gap_sum
 extra_cost={'historical_rows':known_components,'range_seconds':[component_min,component_max],
  'capture_total_range_seconds':[min(x['capture_helper_total_seconds'] for x in cost['rows']),max(x['capture_helper_total_seconds'] for x in cost['rows'])],
  'do_not_double_count':'capture total includes pre-POST readiness wait. Its1.52..4.53s is not added wholesale after sampling at5s.',
  'arm_to_key_POST_observed_seconds':arm_to_key,'latest_historical_target_status_mapped_to_arm_seconds':arm_to_key+longest['HTTP_observation_gap_ms']/1000,
  'sample_START_at_arm5_with_real_observe_child_proxy_seconds':later_start,
  'plus_known_tail_components_range_seconds':[later_start+component_min,later_start+component_max],
  'remaining_seconds_before_unmeasured_pin_pre_POST_flow_adapter_tail':[20-later_start-component_max,20-later_start-component_min],
  'unknown_extra':'Standalone r26 pin pre-POST checks/readiness, flow guards, adapter/image-return tails and future model/scheduler distribution. Post-POST tail is not full standalone pin.'}
 save('LATER-FIRST-OBSERVATION-SCENARIOS.json',{
  'historical_source_scope':timing['scope'],'longest_key_POST_to_target_status_observed_seconds':longest['HTTP_observation_gap_ms']/1000,'step':longest['step'],
  'sampling_proposal':'Only a future offline host candidate: take first read-only image around arm+4.5 to5.0s, retain original 20s countdown and all identity gates, no automatic semantic completion/pin/confirm. Not implemented here.',
  'measured_two_review_handoff_sum_seconds':gap_sum,'scenarios':scenarios,'historical_pin_confirm_components':extra_cost,
  'two_observation_path_conditional_subtotal_seconds':armed_to_observation_return+gap_sum+observe+min(spans),
  'two_observation_assumption':'Use the smaller measured B handoff once more for the extra observe; real pin+confirm still set to zero; not a guaranteed lower bound.',
  'limitations':['Historical 4.496s is HTTP observation, not exact render/native completion or a future upper bound','Sampling later raises probability of a complete first image but does not prove semantic correctness','Single B chain is not a latency distribution or stable runtime guarantee','Real pin/confirm and model/scheduler variability remain unmeasured','If first image is still transitional, only explicit extra observe or End remains; no repin or retry permission'],
  'recommendation':'No new VM based on present evidence; later-first sampling is a narrow future offline proposal with only about2s unallocated budget, not a solved20s contract.'})
save('REHEARSAL-MEASUREMENTS.json',{'groups':groups,'max_groups_authorized':2,'no_sleep_used_as_model_delay':True,'clock_domain':'record each Node timeOrigin; cross-call uses epoch mapping, with wall-clock limitations; historical host_ns is never subtracted from it'})
print(json.dumps({'historical_conditional_budget_seconds':lo,'groups':[(x['group'],x['measured_node_entry_to_confirm_finish_seconds'],x['observed_inter_call_spans_seconds']) for x in groups]}))
