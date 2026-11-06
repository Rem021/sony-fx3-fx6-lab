#!/usr/bin/env python3
"""Readback of sequential reselection, independent packing and owner guard."""
from pathlib import Path
import datetime
import json
import struct
import reselection as t


def phases(case):
    for i,e in enumerate(case['events']):
        assert int(e['SP_after'],16)%16==0
        if i==0:assert e['native_output_or_return_adapter'] is False
        else:
            assert e['native_output_or_PC_return_adapter'] is False
            chunks=e['same_instance_observation_slices']
            assert sum(x['executed'] for x in chunks)==len(e['pcs'])<=2000000
            assert all(a['end_pc']==b['start_pc'] for a,b in zip(chunks,chunks[1:]))
            assert chunks[-1]['reason']==e['reason']


def main():
    t.im.volume();s=t.STAGE;out=s/'completed-evidence-review.json';assert not out.exists()
    prior=t.p.STAGE/'final-receipt.json'
    assert t.im.sha(prior.read_bytes())=='e0cf1c37bc032542958e19b9a4c42ee50949a570d8cd80908c25274bd857b2df'
    j=json.loads(prior.read_text());assert len(j['files'])==24
    for row in j['files']:assert t.im.sha((t.ROOT/row['path']).read_bytes())==row['sha256']
    assert (s/'goal-status-before.json').read_bytes()==(t.BASE/'GOAL_STATUS.json').read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    p=s/'run-explicit-packer-stop-20261026/reselection-results.json';result=json.loads(p.read_text())
    source=(s/'reselection.py').read_bytes()
    assert result['source_receipt']['script_sha256']==t.im.sha(source)
    assert (p.parent/'executed-source.py').read_bytes()==source
    assert result['source_receipt']['storage_runner_sha256']==t.im.sha((t.p.STAGE/'private_storage.py').read_bytes())
    assert result['source_receipt']['writer_object_sha256']==t.im.sha((t.p.STAGE/'run-20261026/resource_alias.a64.o').read_bytes())
    assert result['source_receipt']['adapter_object_sha256']==t.im.sha((t.p.STAGE/'run-20261026/channel_adapter.a64.o').read_bytes())
    assert len(result['cases'])==3 and result['bounded_fragments']==29
    for case in result['cases']:
        phases(case);changed=case['reselected'];events=case['events']
        assert len(events)==(10 if changed else 9)
        a=events[6];b=events[8 if changed else 7]
        assert a['decoded_trace_target_CPB']==[25999360,16000000,26000000]
        assert b['decoded_trace_target_CPB']==[25999360,24498176 if changed else 16000000,26000000]
        assert a['standalone_fragment_not_complete_Start_or_submission'] and b['standalone_fragment_not_complete_Start_or_submission']
        assert a['stop_pc']==b['stop_pc']==hex(t.V+0x22211c)
        assert a['reason']==b['reason']=='boundary: after_original_rate_fields_before_other_inputs'
        first=bytes.fromhex(a['partial_packet64_hex']);second=bytes.fromhex(case['second_packet64_hex'])
        assert second==bytes.fromhex(b['partial_packet64_hex'])
        assert case['packet_changed_offsets']==([45,46,47] if changed else [])
        assert [i for i,(x,y) in enumerate(zip(first,second)) if x!=y]==case['packet_changed_offsets']
        assert case['selection_before']==hex(t.p.PRIVATE)
        assert case['selection_after']==hex(t.V+0x3c5798 if changed else t.p.PRIVATE)
        old=case['control_before'];new=case['control_after']
        assert old['live']==old['phase']==1 and old['gate']==1 and old['fault']==0
        for key in ('owner','epoch','observed_epoch','session'):assert old[key]==new[key]
        if changed:
            assert case['writer_reentry_result']==13 and new['fault']==13 and new['gate']==0 and new['live']==1
            assert case['original_selector_stores']
        else:
            assert case['writer_reentry_result']==0 and new['fault']==0 and new['gate']==1 and new['live']==2
            assert not case['original_selector_stores']
        assert new['phase']==1 and new['lock']==0
        for key in ('original_selector_did_not_update_private_control','first_packet_unchanged_after_original_reselection',
                    'pending_original_query_result_and_stack_unchanged','dedicated_preset_and_guards_unchanged',
                    'source_FH_and_presetID_unchanged','sequential_independent_entries_not_real_concurrency_or_legal_reentrant_API_proof'):
            assert case[key]
        q=case['corrected_query_frame']
        assert q['container_bytes']==56 and q['saved_LR_unchanged'] and not q['stores_outside_declared_container']
        assert q['decoded_trace_target_CPB']==[25999360,16000000,26000000]
        assert not case['actual_Start_transport_completion_main_recording_or_recovery_proven']
    blob=(t.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert t.im.sha(blob)==result['source_receipt']['avcam_sha256']==t.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    for region in result['original_regions']:
        assert region['instructions']==t.im.dump(blob,int(region['start'],16),int(region['end'],16),t.V)
    candidates=[]
    for at in range(0,0x300000,4):
        word=struct.unpack_from('<I',blob,at)[0]
        if word&0x7c000000!=0x14000000:continue
        d=word&0x3ffffff
        if d&0x2000000:d-=0x4000000
        if at+d*4==0x2261a4:candidates.append(at)
    assert candidates==[0x21ee98]
    original_selector=t.im.dump(blob,0x21ee80,0x21eeb8,t.V)
    assert any(x['offset']=='0x21ee98' and x['asm']=='bl #0xffffffc0012261a4' for x in original_selector)
    # Keep the failed missing-stop attempt. It reached the next original
    # input field; bounded-write observation stopped it, not firmware failure.
    failed=s/'run-20261026';first_source=(failed/'attempt-source.py').read_bytes()
    assert first_source==source.replace(b"    m.boundaries[V+0x22211c]='after_original_rate_fields_before_other_inputs'\n",b'')
    f=json.loads((failed/'failure-state.json').read_text())
    assert f['pc']==hex(t.V+0x222120) and not json.loads((failed/'attempt-failure.json').read_text())['passing_result']
    assert not (failed/'reselection-results.json').exists()
    audit={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'direct_B_BL_candidates_first_0x300000_for_selector':[hex(x) for x in candidates],
        'original_straight_line_Open_selection_precedes_adapter_publication':True,
        'not_indirect_or_whole_program_coverage':True,
        'later_first_Start_natural_reselection_or_runtime_collision_proven':False,
        'sequential_counterexample':'Native sameID selector changes current pointer/default future partial packet while prepared16M packet remains. Private token/epoch does not track this original state automatically.',
        'private_gate_scope':'Writer re-entry closes only its own gate on OWNER13, retains live dependency and external selection. Not camera stop, Sony rollback or resource completion.',
        'packet_scope':'Original221fd0..22211c fragment only. Not a full Start request, send, codec acceptance or produced bitstream.',
        'goal_complete':False,'persistent_write_release':False}
    t.im.write_json(s/'selector-caller-and-packet-scope.json',audit)
    review={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_SEQUENTIAL_RESELECTION_PACKET_DIVERGENCE_AND_PRIVATE_OWNER_GUARD_SCOPE',
        'prior_sealed_files_verified':24,'reselection_cases':2,'no_reselection_control':1,'total_bounded_fragments':29,
        'prepared16M_packet_retained_future_partial_packet_returns24498176':True,
        'private_gate_closes_on_reentry_without_overwriting_external_selection_or_dropping_live_dependency':True,
        'no_reselection_control_still16M_and_admits_second_declared_producer':True,
        'fixed56_result_and_dedicated_storage_and_suspended_stack_preserved':True,
        'retained_attempt':'Initial runner omitted explicit22211c fragment stop, next-field write hit the bounded observer at222120; original bytes unchanged and rerun with stop registered.',
        'real_reentrancy_concurrency_config_epoch_complete_Start_main_recording_or_recovery_proven':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    t.im.write_json(out,review)
    print(json.dumps({'status':review['status'],'bounded_fragments':29,'runtime_concurrency_proven':False}))


if __name__=='__main__':main()
